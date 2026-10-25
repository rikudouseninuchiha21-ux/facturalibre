"""Tests de Libro Mayor, Balance de Prueba y cierre de periodos."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.application.auth.security import hash_session_token
from app.domain.models.accounting import (
    AccountingEntry,
    AccountingEntryLine,
    AccountingEntryStatus,
    AccountingSourceType,
)
from app.domain.models.auth import AuthSession, User, UserRole

TWOPLACES = Decimal("0.01")


def _money(value: object) -> Decimal:
    return Decimal(str(value)).quantize(TWOPLACES)


def _setup_sales_catalog(client: TestClient) -> str:
    item = client.post(
        "/api/v1/items",
        json={
            "name": f"Producto contable avanzado {uuid4().hex}",
            "description": "Producto para reportes contables",
            "unit_price": "100.00",
            "tax_id": None,
        },
    )
    assert item.status_code == 201, item.text

    warehouse = client.post(
        "/api/v1/warehouses",
        json={"name": f"Bodega avanzada {uuid4().hex}", "code": uuid4().hex[:12]},
    )
    assert warehouse.status_code == 201, warehouse.text

    movement = client.post(
        "/api/v1/inventory/movements",
        json={
            "item_id": item.json()["id"],
            "warehouse_id": warehouse.json()["id"],
            "movement_type": "IN",
            "quantity": "100",
        },
    )
    assert movement.status_code == 201, movement.text
    return str(item.json()["id"])


def _create_invoice(
    client: TestClient,
    *,
    item_id: str,
    issue_date: date,
    total: str,
) -> dict[str, Any]:
    contact = client.post(
        "/api/v1/contacts",
        json={
            "name": f"Cliente contable {uuid4().hex}",
            "email": f"{uuid4()}@example.com",
        },
    )
    assert contact.status_code == 201, contact.text

    response = client.post(
        "/api/v1/invoices",
        headers={"Idempotency-Key": str(uuid4())},
        json={
            "contact_id": contact.json()["id"],
            "issue_date": issue_date.isoformat(),
            "due_date": (issue_date + timedelta(days=30)).isoformat(),
            "currency": "COP",
            "lines": [
                {
                    "item_id": item_id,
                    "quantity": "1",
                    "unit_price": total,
                    "discount_percent": "0",
                    "tax_rate": "0",
                }
            ],
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def _issue_invoice(
    client: TestClient,
    *,
    item_id: str,
    issue_date: date,
    total: str,
) -> dict[str, Any]:
    invoice = _create_invoice(
        client,
        item_id=item_id,
        issue_date=issue_date,
        total=total,
    )
    response = client.post(f"/api/v1/invoices/{invoice['id']}/issue")
    assert response.status_code == 200, response.text
    return response.json()


def _make_client_with_role(
    db_session: Session,
    role: UserRole,
) -> TestClient:
    """Crea un cliente autenticado con el rol indicado."""
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

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app, base_url="https://testserver")
    client.cookies.set("facturalibre_session", token, path="/")
    return client


def test_close_period_blocks_new_entries(client: TestClient, db_session: Session) -> None:
    item_id = _setup_sales_catalog(client)
    today = date.today()
    invoice = _create_invoice(
        client,
        item_id=item_id,
        issue_date=today,
        total="100.00",
    )

    close = client.post(
        "/api/v1/accounting/close-period",
        json={"month": today.month, "year": today.year},
    )
    assert close.status_code == 200, close.text
    period = close.json()
    assert period["status"] == "CLOSED"
    assert period["month"] == today.month
    assert period["year"] == today.year
    assert period["closed_at"] is not None

    blocked = client.post(f"/api/v1/invoices/{invoice['id']}/issue")
    assert blocked.status_code == 409, blocked.text
    assert "cerrado" in blocked.json()["detail"].lower()

    unchanged = client.get(f"/api/v1/invoices/{invoice['id']}")
    assert unchanged.status_code == 200, unchanged.text
    assert unchanged.json()["lifecycle_status"] == "draft"
    assert db_session.scalar(select(func.count()).select_from(AccountingEntry)) == 0

    repeated = client.post(
        "/api/v1/accounting/close-period",
        json={"month": today.month, "year": today.year},
    )
    assert repeated.status_code == 409, repeated.text
    assert "ya está cerrado" in repeated.json()["detail"].lower()


def test_close_period_rejects_unbalanced_entries(
    client: TestClient,
    db_session: Session,
) -> None:
    today = date.today()
    entry = AccountingEntry(
        entry_date=today,
        description="Asiento descuadrado de prueba",
        source_type=AccountingSourceType.INVOICE,
        source_id=uuid4(),
        status=AccountingEntryStatus.POSTED,
        lines=[
            AccountingEntryLine(
                account_code="130505",
                debit=Decimal("10.00"),
                credit=Decimal("0.00"),
            )
        ],
    )
    db_session.add(entry)
    db_session.flush()

    response = client.post(
        "/api/v1/accounting/close-period",
        json={"month": today.month, "year": today.year},
    )
    assert response.status_code == 409, response.text
    assert "descuadrados" in response.json()["detail"].lower()


def test_ledger_includes_opening_balance_and_movements(client: TestClient) -> None:
    item_id = _setup_sales_catalog(client)
    today = date.today()
    if today.month == 1:
        previous_month_date = date(today.year - 1, 12, 15)
    else:
        previous_month_date = date(today.year, today.month - 1, 15)
    current_start = today.replace(day=1)

    _issue_invoice(
        client,
        item_id=item_id,
        issue_date=previous_month_date,
        total="100.00",
    )
    _issue_invoice(
        client,
        item_id=item_id,
        issue_date=today,
        total="50.00",
    )

    response = client.get(
        "/api/v1/reports/ledger",
        params={
            "account_code": "130505",
            "start_date": current_start.isoformat(),
            "end_date": today.isoformat(),
        },
    )
    assert response.status_code == 200, response.text
    report = response.json()
    assert report["account_code"] == "130505"
    assert report["account_name"] == "Clientes nacionales"
    assert _money(report["opening_balance"]) == Decimal("100.00")
    assert _money(report["total_debits"]) == Decimal("50.00")
    assert _money(report["total_credits"]) == Decimal("0.00")
    assert _money(report["closing_balance"]) == Decimal("150.00")
    assert len(report["movements"]) == 1
    movement = report["movements"][0]
    assert movement["entry_date"] == today.isoformat()
    assert _money(movement["debit"]) == Decimal("50.00")
    assert _money(movement["balance"]) == Decimal("150.00")

    income_response = client.get(
        "/api/v1/reports/ledger",
        params={"account_code": "413505"},
    )
    assert income_response.status_code == 200, income_response.text
    income_report = income_response.json()
    assert _money(income_report["opening_balance"]) == Decimal("0.00")
    assert _money(income_report["total_credits"]) == Decimal("150.00")
    assert _money(income_report["closing_balance"]) == Decimal("150.00")
    assert len(income_report["movements"]) == 2


def test_trial_balance_is_balanced_and_classifies_accounts(
    client: TestClient,
) -> None:
    item_id = _setup_sales_catalog(client)
    today = date.today()
    _issue_invoice(
        client,
        item_id=item_id,
        issue_date=today,
        total="100.00",
    )

    response = client.get(
        "/api/v1/reports/trial-balance",
        params={"as_of_date": today.isoformat()},
    )
    assert response.status_code == 200, response.text
    report = response.json()
    assert report["balanced"] is True
    assert _money(report["difference"]) == Decimal("0.00")
    assert _money(report["total_debit"]) == _money(report["total_credit"])

    accounts = {row["code"]: row for row in report["accounts"]}
    assert _money(accounts["130505"]["debit"]) == Decimal("100.00")
    assert _money(accounts["130505"]["balance"]) == Decimal("100.00")
    assert accounts["130505"]["balance_type"] == "DEUDOR"
    assert _money(accounts["413505"]["credit"]) == Decimal("100.00")
    assert _money(accounts["413505"]["balance"]) == Decimal("100.00")
    assert accounts["413505"]["balance_type"] == "ACREEDOR"


def test_ledger_account_search_and_validation(client: TestClient) -> None:
    response = client.get(
        "/api/v1/reports/ledger/accounts",
        params={"search": "Clientes"},
    )
    assert response.status_code == 200, response.text
    codes = {account["code"] for account in response.json()}
    assert "130505" in codes

    missing = client.get(
        "/api/v1/reports/ledger",
        params={"account_code": "999999"},
    )
    assert missing.status_code == 404

    invalid_range = client.get(
        "/api/v1/reports/ledger",
        params={
            "account_code": "130505",
            "start_date": "2026-12-31",
            "end_date": "2026-01-01",
        },
    )
    assert invalid_range.status_code == 422


def test_advanced_reports_require_authentication(
    anonymous_client: TestClient,
) -> None:
    assert anonymous_client.get("/api/v1/reports/ledger?account_code=130505").status_code == 401
    assert anonymous_client.get("/api/v1/reports/trial-balance").status_code == 401
    assert (
        anonymous_client.post(
            "/api/v1/accounting/close-period",
            json={"month": 1, "year": 2026},
        ).status_code
        == 401
    )


def test_roles_for_advanced_reports_and_close_period(
    db_session: Session,
) -> None:
    accountant = _make_client_with_role(db_session, UserRole.ACCOUNTANT)
    assert accountant.get("/api/v1/reports/ledger?account_code=130505").status_code == 200
    assert accountant.get("/api/v1/reports/trial-balance").status_code == 200
    assert (
        accountant.post(
            "/api/v1/accounting/close-period",
            json={"month": 1, "year": 2026},
        ).status_code
        == 403
    )

    cashier = _make_client_with_role(db_session, UserRole.CASHIER)
    assert cashier.get("/api/v1/reports/trial-balance").status_code == 403

    admin = _make_client_with_role(db_session, UserRole.ADMIN)
    response = admin.post(
        "/api/v1/accounting/close-period",
        json={"month": 1, "year": 2026},
    )
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "CLOSED"
