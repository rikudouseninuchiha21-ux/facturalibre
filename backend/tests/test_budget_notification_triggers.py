"""Tests de los disparadores de notificaciones de presupuestos (Fase 35 → 36)."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.domain.models.accounting import (
    AccountingEntry,
    AccountingEntryLine,
    AccountingEntryStatus,
    AccountingSourceType,
)
from app.domain.models.auth import UserRole

ZERO = Decimal("0.00")

# Mes de cierre para los tests de close_by_period (abierto en la base de test).
CLOSE_YEAR = 2026
CLOSE_MONTH = 4


def _make_client_with_role(db_session: Session, role: UserRole) -> TestClient:
    """Crea un usuario activo del rol indicado y un cliente autenticado."""
    from app.application.auth.security import hash_session_token
    from app.domain.models.auth import AuthSession, User
    from app.infrastructure.database import get_db
    from app.main import app

    user = User(
        email=f"{role.value.lower()}-{uuid4()}@example.com",
        hashed_password="dummy-hash",
        full_name=f"Usuario {role.value}",
        role=role,
        is_active=True,
    )
    db_session.add(user)
    db_session.flush()

    token = str(uuid4())
    db_session.add(
        AuthSession(
            user_id=user.id,
            token=hash_session_token(token),
            expires_at=datetime.now(UTC) + timedelta(hours=1),
        )
    )
    db_session.flush()

    def override_get_db() -> Any:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app, base_url="https://testserver")
    client.cookies.set("facturalibre_session", token, path="/")
    return client


def _create_cost_center(client: TestClient) -> dict[str, Any]:
    response = client.post(
        "/api/v1/cost-centers",
        json={"code": f"CC-{uuid4().hex[:8].upper()}", "name": "Triggers"},
    )
    assert response.status_code == 201, response.text
    return response.json()


def _create_approved_budget(
    client: TestClient,
    cost_center_id: str,
    *,
    budgeted: str,
    month: int | None = None,
    year: int | None = None,
) -> dict[str, Any]:
    today = date.today()
    budget = client.post(
        "/api/v1/budgets",
        json={
            "cost_center_id": cost_center_id,
            "period_year": year or today.year,
            "period_month": month or today.month,
        },
    )
    assert budget.status_code == 201, budget.text
    budget = budget.json()

    line = client.post(
        f"/api/v1/budgets/{budget['id']}/lines",
        json={"account_code": "5199", "amount": budgeted},
    )
    assert line.status_code == 201, line.text

    approved = client.post(f"/api/v1/budgets/{budget['id']}/approve")
    assert approved.status_code == 200, approved.text
    return budget


def _create_expense(
    client: TestClient,
    cost_center_id: str,
    amount: str,
    *,
    day: int | None = None,
) -> dict[str, Any]:
    today = date.today()
    response = client.post(
        "/api/v1/expenses",
        json={
            "date": date(today.year, today.month, day or 10).isoformat(),
            "concept": "Gasto de prueba",
            "amount": amount,
            "payment_method": "efectivo",
            "cost_center_id": cost_center_id,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def _notifications(client: TestClient, category: str) -> list[dict[str, Any]]:
    response = client.get("/api/v1/notifications?limit=100")
    assert response.status_code == 200, response.text
    return [item for item in response.json() if item["category"] == category]


def test_threshold_crossing_warning_notifies(
    client: TestClient,
    db_session: Session,
) -> None:
    accountant = _make_client_with_role(db_session, UserRole.ACCOUNTANT)
    center = _create_cost_center(client)
    budget = _create_approved_budget(client, center["id"], budgeted="100000.00")

    _create_expense(client, center["id"], "85000.00")

    admin_alerts = _notifications(client, "BUDGET_ALERT")
    assert len(admin_alerts) == 1, admin_alerts
    alert = admin_alerts[0]
    assert alert["severity"] == "WARNING"
    assert alert["link"] == f"/budgets/{budget['id']}"
    assert center["name"] in alert["title"]

    # El contador (ACCOUNTANT) también recibe la alerta.
    accountant_alerts = _notifications(accountant, "BUDGET_ALERT")
    assert len(accountant_alerts) == 1
    assert accountant_alerts[0]["severity"] == "WARNING"


def test_threshold_crossing_critical_and_over(
    client: TestClient,
    db_session: Session,
) -> None:
    critical_center = _create_cost_center(client)
    _create_approved_budget(client, critical_center["id"], budgeted="100000.00")
    _create_expense(client, critical_center["id"], "95000.00")

    alerts = _notifications(client, "BUDGET_ALERT")
    assert len(alerts) == 1
    assert alerts[0]["severity"] == "CRITICAL"

    over_center = _create_cost_center(client)
    over_budget = _create_approved_budget(client, over_center["id"], budgeted="100000.00")
    _create_expense(client, over_center["id"], "110000.00")

    over_alerts = [
        item
        for item in _notifications(client, "BUDGET_ALERT")
        if item["link"] == f"/budgets/{over_budget['id']}"
    ]
    assert len(over_alerts) == 1
    # OVER (sobregiro) también se notifica como CRITICAL.
    assert over_alerts[0]["severity"] == "CRITICAL"


def test_no_duplicate_notifications_when_level_unchanged(
    client: TestClient,
    db_session: Session,
) -> None:
    center = _create_cost_center(client)
    _create_approved_budget(client, center["id"], budgeted="200000.00")

    # 50% → OK; 75% → OK (sin notif); 85% → WARNING (notif); 87.5% → WARNING
    # otra vez, pero el nivel no cambia: no debe duplicar notificaciones.
    for amount in ("100000.00", "50000.00", "20000.00", "5000.00"):
        _create_expense(client, center["id"], amount)

    alerts = _notifications(client, "BUDGET_ALERT")
    assert len(alerts) == 1, alerts
    assert alerts[0]["severity"] == "WARNING"


def test_approve_notifies_admin_and_accountant(
    client: TestClient,
    db_session: Session,
) -> None:
    accountant = _make_client_with_role(db_session, UserRole.ACCOUNTANT)
    center = _create_cost_center(client)
    budget = _create_approved_budget(client, center["id"], budgeted="50000.00")

    admin_notifs = _notifications(client, "BUDGET_APPROVED")
    assert len(admin_notifs) == 1
    assert admin_notifs[0]["severity"] == "INFO"
    assert admin_notifs[0]["link"] == f"/budgets/{budget['id']}"

    accountant_notifs = _notifications(accountant, "BUDGET_APPROVED")
    assert len(accountant_notifs) == 1
    assert accountant_notifs[0]["severity"] == "INFO"


def test_close_period_notifies_only_admins(
    client: TestClient,
    db_session: Session,
) -> None:
    accountant = _make_client_with_role(db_session, UserRole.ACCOUNTANT)
    center = _create_cost_center(client)
    budget = _create_approved_budget(
        client, center["id"], budgeted="1000.00", month=CLOSE_MONTH, year=CLOSE_YEAR
    )

    closed = client.post(
        "/api/v1/accounting/close-period",
        json={"month": CLOSE_MONTH, "year": CLOSE_YEAR},
    )
    assert closed.status_code == 200, closed.text

    admin_notifs = _notifications(client, "BUDGET_CLOSED")
    assert len(admin_notifs) == 1
    assert admin_notifs[0]["link"] == f"/budgets/{budget['id']}"
    assert admin_notifs[0]["severity"] == "INFO"

    # El cierre automático solo notifica a ADMIN.
    assert _notifications(accountant, "BUDGET_CLOSED") == []


def test_failed_close_period_leaves_no_orphan_notifications(
    client: TestClient,
    db_session: Session,
) -> None:
    center = _create_cost_center(client)
    _create_approved_budget(
        client, center["id"], budgeted="1000.00", month=CLOSE_MONTH, year=CLOSE_YEAR
    )

    # Asiento descuadrado en el mes: el cierre del periodo falla (409) y la
    # transacción revierte también las notificaciones del disparador.
    unbalanced = AccountingEntry(
        entry_date=date(CLOSE_YEAR, CLOSE_MONTH, 15),
        description="Asiento descuadrado de prueba",
        source_type=AccountingSourceType.INVOICE,
        source_id=uuid4(),
        status=AccountingEntryStatus.POSTED,
        lines=[
            AccountingEntryLine(
                account_code="5199",
                debit=Decimal("10.00"),
                credit=ZERO,
            )
        ],
    )
    db_session.add(unbalanced)
    db_session.flush()

    failed = client.post(
        "/api/v1/accounting/close-period",
        json={"month": CLOSE_MONTH, "year": CLOSE_YEAR},
    )
    assert failed.status_code == 409, failed.text

    assert _notifications(client, "BUDGET_CLOSED") == []
