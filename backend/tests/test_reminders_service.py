"""Tests del servicio de recordatorios de cobranza."""

from __future__ import annotations
from uuid import UUID

from datetime import date, timedelta
from decimal import Decimal
from typing import Any
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.application.notification_service import NotificationService
from app.application.reminder_service import ReminderService
from app.domain.exceptions import ReceivablesValidationError
from app.domain.models.auth import User, UserRole
from app.domain.models.notification import NotificationSeverity

TWOPLACES = Decimal("0.01")


def _money(value: object) -> Decimal:
    return Decimal(str(value)).quantize(TWOPLACES)


def _make_user(db_session: Session, *, role: UserRole) -> User:
    user = User(
        email=f"{role.value.lower()}-{uuid4()}@example.com",
        hashed_password="dummy-hash",
        full_name=f"Usuario {role.value}",
        role=role,
        is_active=True,
    )
    db_session.add(user)
    db_session.flush()
    return user


def _setup_catalog(client: TestClient) -> tuple[UUID, str]:
    suffix = uuid4().hex[:8].upper()
    contact = client.post(
        "/api/v1/contacts",
        json={"name": f"Cliente Cobranza {suffix}", "email": f"cobro-{suffix}@example.com"},
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
            "quantity": "500",
        },
    )
    assert movement.status_code == 201, movement.text
    return UUID(contact.json()["id"]), str(item.json()["id"])


def _create_issued_invoice(
    client: TestClient,
    *,
    contact_id: UUID,
    item_id: str,
    total: str,
    issue_date: date,
    due_date: date,
) -> dict[str, Any]:
    response = client.post(
        "/api/v1/invoices",
        json={
            "contact_id": str(contact_id),
            "issue_date": issue_date.isoformat(),
            "due_date": due_date.isoformat(),
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


def _pay(client: TestClient, invoice_id: str, amount: str) -> None:
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


def test_send_reminder_persists_and_notifies(
    client: TestClient,
    db_session: Session,
) -> None:
    admin = _make_user(db_session, role=UserRole.ADMIN)
    accountant = _make_user(db_session, role=UserRole.ACCOUNTANT)
    contact_id, item_id = _setup_catalog(client)
    today = date(2026, 10, 25)
    invoice = _create_issued_invoice(
        client,
        contact_id=contact_id,
        item_id=item_id,
        total="80000.00",
        issue_date=today - timedelta(days=20),
        due_date=today - timedelta(days=20),
    )

    service = ReminderService(db_session)
    reminder = service.send_reminder(
        invoice_id=invoice["id"],
        level=2,
        notes="Llamada de cortesía",
        created_by=admin.id,
    )
    assert reminder is not None
    assert reminder.level == 2
    assert reminder.contact_id == contact_id
    assert reminder.notes == "Llamada de cortesía"

    notifications = NotificationService(db_session)
    for user in (admin, accountant):
        items = notifications.list_for_user(user_id=user.id)
        matching = [item for item in items if item.category == "PAYMENT_REMINDER"]
        assert len(matching) == 1
        assert matching[0].severity is NotificationSeverity.INFO
        assert matching[0].link == f"/receivables/customers/{contact_id}"


def test_paid_invoice_cannot_be_reminded(
    client: TestClient,
    db_session: Session,
) -> None:
    admin = _make_user(db_session, role=UserRole.ADMIN)
    contact_id, item_id = _setup_catalog(client)
    today = date(2026, 10, 25)
    invoice = _create_issued_invoice(
        client,
        contact_id=contact_id,
        item_id=item_id,
        total="50000.00",
        issue_date=today - timedelta(days=25),
        due_date=today - timedelta(days=25),
    )
    _pay(client, str(invoice["id"]), "50000.00")

    with pytest.raises(ReceivablesValidationError):
        ReminderService(db_session).send_reminder(
            invoice_id=invoice["id"],
            level=1,
            created_by=admin.id,
        )


def test_duplicate_level_within_24h_is_skipped(
    client: TestClient,
    db_session: Session,
) -> None:
    admin = _make_user(db_session, role=UserRole.ADMIN)
    contact_id, item_id = _setup_catalog(client)
    today = date(2026, 10, 25)
    invoice = _create_issued_invoice(
        client,
        contact_id=contact_id,
        item_id=item_id,
        total="30000.00",
        issue_date=today - timedelta(days=15),
        due_date=today - timedelta(days=15),
    )

    service = ReminderService(db_session)
    first = service.send_reminder(invoice_id=invoice["id"], level=1, created_by=admin.id)
    second = service.send_reminder(invoice_id=invoice["id"], level=1, created_by=admin.id)
    third = service.send_reminder(invoice_id=invoice["id"], level=2, created_by=admin.id)

    assert first is not None
    assert second is None
    assert third is not None


def test_auto_remind_uses_days_buckets_and_is_idempotent(
    client: TestClient,
    db_session: Session,
) -> None:
    admin = _make_user(db_session, role=UserRole.ADMIN)
    contact_id, item_id = _setup_catalog(client)
    today = date(2026, 10, 25)
    for days in (3, 10, 20, 35, 50, 70):
        _create_issued_invoice(
            client,
            contact_id=contact_id,
            item_id=item_id,
            total="10000.00",
            issue_date=today - timedelta(days=days),
            due_date=today - timedelta(days=days),
        )

    service = ReminderService(db_session)
    first = service.auto_remind_overdue(as_of_date=today, created_by=admin.id)
    assert first == {"created": 5, "skipped": 1, "errors": 0}

    reminders = service.list_reminders(contact_id=contact_id)
    assert sorted(item.level for item in reminders) == [1, 2, 3, 4, 5]

    second = service.auto_remind_overdue(as_of_date=today, created_by=admin.id)
    assert second == {"created": 0, "skipped": 6, "errors": 0}
    assert len(service.list_reminders(contact_id=contact_id)) == 5


def test_level_4_notification_is_critical(
    client: TestClient,
    db_session: Session,
) -> None:
    admin = _make_user(db_session, role=UserRole.ADMIN)
    accountant = _make_user(db_session, role=UserRole.ACCOUNTANT)
    contact_id, item_id = _setup_catalog(client)
    today = date(2026, 10, 25)
    invoice = _create_issued_invoice(
        client,
        contact_id=contact_id,
        item_id=item_id,
        total="42000.00",
        issue_date=today - timedelta(days=55),
        due_date=today - timedelta(days=55),
    )

    ReminderService(db_session).send_reminder(
        invoice_id=invoice["id"],
        level=4,
        created_by=admin.id,
    )

    notifications = NotificationService(db_session)
    for user in (admin, accountant):
        items = notifications.list_for_user(user_id=user.id)
        matching = [item for item in items if item.category == "PAYMENT_REMINDER"]
        assert len(matching) == 1
        assert matching[0].severity is NotificationSeverity.CRITICAL
