"""Tests de rutas y RBAC de cartera."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from typing import Any
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.application.auth.security import SESSION_COOKIE_NAME, hash_session_token
from app.domain.models.auth import AuthSession, User, UserRole


def _make_client_with_role(db_session: Session, role: UserRole) -> TestClient:
    """Crea un TestClient autenticado con el rol indicado."""
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
    test_client = TestClient(app, base_url="https://testserver")
    test_client.cookies.set(SESSION_COOKIE_NAME, token, path="/")
    return test_client


def _clear_overrides() -> None:
    from app.main import app

    app.dependency_overrides.clear()


def _setup_catalog(client: TestClient) -> tuple[str, str]:
    suffix = uuid4().hex[:8].upper()
    contact = client.post(
        "/api/v1/contacts",
        json={"name": f"Cliente Router {suffix}", "email": f"router-{suffix}@example.com"},
    )
    assert contact.status_code == 201, contact.text
    item = client.post(
        "/api/v1/items",
        json={
            "name": f"Producto {suffix}",
            "description": "Producto de prueba",
            "unit_price": "1.00",
            "tax_id": None,
        },
    )
    assert item.status_code == 201, item.text
    warehouse = client.post(
        "/api/v1/warehouses",
        json={"name": f"Bodega {suffix}", "code": f"WH{suffix}"},
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
    return str(contact.json()["id"]), str(item.json()["id"])


def _create_issued_invoice(
    client: TestClient,
    *,
    contact_id: str,
    item_id: str,
    total: str,
) -> dict[str, Any]:
    today = date(2026, 10, 25)
    response = client.post(
        "/api/v1/invoices",
        json={
            "contact_id": contact_id,
            "issue_date": (today - timedelta(days=30)).isoformat(),
            "due_date": (today - timedelta(days=10)).isoformat(),
            "currency": "COP",
            "lines": [
                {
                    "item_id": item_id,
                    "quantity": "1",
                    "unit_price": total,
                    "discount_percent": "0",
                }
            ],
        },
        headers={"Idempotency-Key": str(uuid4())},
    )
    assert response.status_code == 201, response.text
    issued = client.post(f"/api/v1/invoices/{response.json()['id']}/issue")
    assert issued.status_code == 200, issued.text
    return issued.json()


def _pay_invoice(client: TestClient, invoice_id: str, amount: str) -> None:
    response = client.post(
        f"/api/v1/invoices/{invoice_id}/payments",
        json={
            "amount": amount,
            "payment_date": date.today().isoformat(),
            "method": "Transferencia",
        },
        headers={"Idempotency-Key": str(uuid4())},
    )
    assert response.status_code == 201, response.text


def test_aging_requires_authentication(anonymous_client: TestClient) -> None:
    response = anonymous_client.get("/api/v1/receivables/aging")
    assert response.status_code == 401


def test_cashier_can_read_aging(db_session: Session) -> None:
    cashier = _make_client_with_role(db_session, UserRole.CASHIER)
    try:
        response = cashier.get("/api/v1/receivables/aging")
        assert response.status_code == 200, response.text
        assert "buckets_totals" in response.json()
    finally:
        _clear_overrides()


def test_cashier_cannot_create_reminder(db_session: Session) -> None:
    cashier = _make_client_with_role(db_session, UserRole.CASHIER)
    try:
        response = cashier.post(
            "/api/v1/receivables/reminders",
            json={"invoice_id": str(uuid4()), "level": 1},
        )
        assert response.status_code == 403, response.text
    finally:
        _clear_overrides()


def test_admin_can_create_reminder_and_duplicate_returns_409(
    db_session: Session,
) -> None:
    admin = _make_client_with_role(db_session, UserRole.ADMIN)
    try:
        contact_id, item_id = _setup_catalog(admin)
        invoice = _create_issued_invoice(
            admin,
            contact_id=contact_id,
            item_id=item_id,
            total="60000.00",
        )
        first = admin.post(
            "/api/v1/receivables/reminders",
            json={"invoice_id": invoice["id"], "level": 2, "notes": "Primer aviso"},
        )
        assert first.status_code == 201, first.text
        assert first.json()["level"] == 2

        duplicate = admin.post(
            "/api/v1/receivables/reminders",
            json={"invoice_id": invoice["id"], "level": 2},
        )
        assert duplicate.status_code == 409, duplicate.text
    finally:
        _clear_overrides()


def test_reminder_on_paid_invoice_returns_422(db_session: Session) -> None:
    admin = _make_client_with_role(db_session, UserRole.ADMIN)
    try:
        contact_id, item_id = _setup_catalog(admin)
        invoice = _create_issued_invoice(
            admin,
            contact_id=contact_id,
            item_id=item_id,
            total="70000.00",
        )
        _pay_invoice(admin, str(invoice["id"]), "70000.00")
        response = admin.post(
            "/api/v1/receivables/reminders",
            json={"invoice_id": invoice["id"], "level": 1},
        )
        assert response.status_code == 422, response.text
    finally:
        _clear_overrides()


def test_agreement_over_invoice_balance_returns_422(db_session: Session) -> None:
    admin = _make_client_with_role(db_session, UserRole.ADMIN)
    try:
        contact_id, item_id = _setup_catalog(admin)
        invoice = _create_issued_invoice(
            admin,
            contact_id=contact_id,
            item_id=item_id,
            total="100000.00",
        )
        response = admin.post(
            "/api/v1/receivables/agreements",
            json={
                "contact_id": contact_id,
                "invoice_id": invoice["id"],
                "total_amount": "100000.01",
                "installments": 2,
                "start_date": "2026-11-01",
            },
        )
        assert response.status_code == 422, response.text
    finally:
        _clear_overrides()
