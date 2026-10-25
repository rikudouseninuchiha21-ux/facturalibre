"""Tests del endpoint GET /api/v1/budgets/alerts."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.application.auth.security import hash_session_token
from app.domain.models.accounting import (
    AccountingEntry,
    AccountingEntryLine,
    AccountingEntryStatus,
    AccountingSourceType,
)
from app.domain.models.auth import AuthSession, User, UserRole

ZERO = Decimal("0.00")

# Periodo fijo del test: noviembre de 2026 (abierto en la base de prueba).
TEST_YEAR = 2026
TEST_MONTH = 11


def _make_client_with_role(db_session: Session, role: UserRole) -> TestClient:
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


def _post_manual_entry(
    db_session: Session,
    *,
    cost_center_id: UUID,
    amount: Decimal,
) -> None:
    entry = AccountingEntry(
        entry_date=date(TEST_YEAR, TEST_MONTH, 10),
        description="Asiento manual para alertas",
        source_type=AccountingSourceType.INVOICE,
        source_id=uuid4(),
        status=AccountingEntryStatus.POSTED,
        lines=[
            AccountingEntryLine(
                account_code="5199",
                debit=amount,
                credit=ZERO,
                cost_center_id=cost_center_id,
            ),
            AccountingEntryLine(
                account_code="110505",
                debit=ZERO,
                credit=amount,
                cost_center_id=cost_center_id,
            ),
        ],
    )
    db_session.add(entry)
    db_session.flush()


def _make_budget(
    client: TestClient,
    db_session: Session,
    *,
    budgeted: str,
    actual: str,
    approve: bool = True,
) -> dict[str, Any]:
    """Crea centro + presupuesto de una línea (5199) con el real indicado."""
    center = client.post(
        "/api/v1/cost-centers",
        json={"code": f"CC-{uuid4().hex[:8].upper()}", "name": "Alertas"},
    )
    assert center.status_code == 201, center.text
    center = center.json()

    budget = client.post(
        "/api/v1/budgets",
        json={
            "cost_center_id": center["id"],
            "period_year": TEST_YEAR,
            "period_month": TEST_MONTH,
        },
    )
    assert budget.status_code == 201, budget.text
    budget = budget.json()

    line = client.post(
        f"/api/v1/budgets/{budget['id']}/lines",
        json={"account_code": "5199", "amount": budgeted},
    )
    assert line.status_code == 201, line.text

    if Decimal(actual) > ZERO:
        _post_manual_entry(
            db_session,
            cost_center_id=UUID(center["id"]),
            amount=Decimal(actual),
        )

    if approve:
        approved = client.post(f"/api/v1/budgets/{budget['id']}/approve")
        assert approved.status_code == 200, approved.text

    return budget


def test_alerts_requires_period_params(client: TestClient) -> None:
    missing_all = client.get("/api/v1/budgets/alerts")
    assert missing_all.status_code == 422, missing_all.text

    missing_month = client.get("/api/v1/budgets/alerts?period_year=2026")
    assert missing_month.status_code == 422, missing_month.text

    missing_year = client.get("/api/v1/budgets/alerts?period_month=11")
    assert missing_year.status_code == 422, missing_year.text


def test_alerts_excludes_draft_and_orders_desc(
    client: TestClient,
    db_session: Session,
) -> None:
    over = _make_budget(client, db_session, budgeted="100000.00", actual="110000.00")
    warning = _make_budget(client, db_session, budgeted="100000.00", actual="85000.00")
    # Un DRAFT con gasto real no aparece: no es compromiso presupuestal aún.
    # (Un APPROVED nunca puede tener total cero — la aprobación lo exige
    # mayor que cero —, así que el endpoint nunca retorna N/A.)
    draft = _make_budget(client, db_session, budgeted="100000.00", actual="50000.00", approve=False)

    response = client.get(
        f"/api/v1/budgets/alerts?period_year={TEST_YEAR}&period_month={TEST_MONTH}"
    )
    assert response.status_code == 200, response.text
    alerts = response.json()

    # Orden DESC por utilización; el DRAFT no aparece.
    assert [item["budget_id"] for item in alerts] == [
        over["id"],
        warning["id"],
    ]
    assert draft["id"] not in {item["budget_id"] for item in alerts}

    first = alerts[0]
    assert first["cost_center"]["id"]
    assert first["cost_center"]["code"]
    assert first["cost_center"]["name"]
    assert Decimal(first["total_budgeted"]) == Decimal("100000.00")
    assert Decimal(first["total_actual"]) == Decimal("110000.00")
    assert Decimal(first["utilization_pct"]) == Decimal("110.00")
    assert first["alert_level"] == "OVER"
    assert first["period_year"] == TEST_YEAR
    assert first["period_month"] == TEST_MONTH


def test_alerts_filters_by_level(client: TestClient, db_session: Session) -> None:
    over = _make_budget(client, db_session, budgeted="100000.00", actual="110000.00")
    warning = _make_budget(client, db_session, budgeted="100000.00", actual="85000.00")

    def by_level(level: str) -> list[str]:
        response = client.get(
            f"/api/v1/budgets/alerts?period_year={TEST_YEAR}"
            f"&period_month={TEST_MONTH}&level={level}"
        )
        assert response.status_code == 200, response.text
        return [item["budget_id"] for item in response.json()]

    assert by_level("OVER") == [over["id"]]
    assert by_level("WARNING") == [warning["id"]]
    assert by_level("CRITICAL") == []

    # El filtro de nivel solo acepta los niveles de riesgo.
    invalid = client.get(
        f"/api/v1/budgets/alerts?period_year={TEST_YEAR}&period_month={TEST_MONTH}&level=OK"
    )
    assert invalid.status_code == 422, invalid.text


def test_alerts_roles(db_session: Session, client: TestClient) -> None:
    cashier = _make_client_with_role(db_session, UserRole.CASHIER)
    response = cashier.get(
        f"/api/v1/budgets/alerts?period_year={TEST_YEAR}&period_month={TEST_MONTH}"
    )
    assert response.status_code == 403, response.text


def test_alerts_requires_authentication(anonymous_client: TestClient) -> None:
    response = anonymous_client.get(
        f"/api/v1/budgets/alerts?period_year={TEST_YEAR}&period_month={TEST_MONTH}"
    )
    assert response.status_code == 401, response.text
