"""Tests de acuerdos de pago y reparto exacto de cuotas."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.application.agreement_service import AgreementService, split_installments
from app.domain.exceptions import AgreementValidationError
from app.domain.models.auth import User, UserRole
from app.domain.models.receivables import AgreementStatus

TWOPLACES = Decimal("0.01")


def _money(value: object) -> Decimal:
    return Decimal(str(value)).quantize(TWOPLACES)


def _make_user(db_session: Session, *, role: UserRole = UserRole.ADMIN) -> User:
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


def _create_contact(client: TestClient) -> UUID:
    suffix = uuid4().hex[:8].upper()
    response = client.post(
        "/api/v1/contacts",
        json={"name": f"Cliente Acuerdo {suffix}", "email": f"acuerdo-{suffix}@example.com"},
    )
    assert response.status_code == 201, response.text
    return UUID(response.json()["id"])


def _setup_catalog(client: TestClient) -> tuple[UUID, str]:
    contact_id = _create_contact(client)
    suffix = uuid4().hex[:8].upper()
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
    return contact_id, str(item.json()["id"])


def _create_issued_invoice(
    client: TestClient,
    *,
    contact_id: UUID,
    item_id: str,
    total: str,
) -> dict[str, Any]:
    today = date(2026, 10, 25)
    response = client.post(
        "/api/v1/invoices",
        json={
            "contact_id": str(contact_id),
            "issue_date": (today - timedelta(days=40)).isoformat(),
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


def test_split_one_million_in_three_has_exact_total() -> None:
    amounts = split_installments(Decimal("1000000.00"), 3)
    assert amounts == [
        Decimal("333333.33"),
        Decimal("333333.33"),
        Decimal("333333.34"),
    ]
    assert sum(amounts, Decimal("0.00")) == Decimal("1000000.00")


def test_create_agreement_generates_installments(
    client: TestClient,
    db_session: Session,
) -> None:
    user = _make_user(db_session)
    contact_id = _create_contact(client)
    start = date(2026, 11, 1)

    agreement = AgreementService(db_session).create(
        contact_id=contact_id,
        invoice_id=None,
        total_amount=Decimal("1000000.00"),
        installments=3,
        start_date=start,
        frequency_days=30,
        notes="Acuerdo de prueba",
        created_by=user.id,
    )

    assert agreement.status is AgreementStatus.ACTIVE
    assert _money(agreement.total_amount) == _money("1000000.00")
    assert len(agreement.installment_items) == 3
    assert _money(agreement.installment_items[0].amount) == _money("333333.33")
    assert _money(agreement.installment_items[2].amount) == _money("333333.34")
    assert agreement.installment_items[0].due_date == start
    assert agreement.installment_items[1].due_date == start + timedelta(days=30)
    assert agreement.installment_items[2].due_date == start + timedelta(days=60)
    assert _money(agreement.paid_total) == _money("0.00")
    assert _money(agreement.balance) == _money("1000000.00")


def test_partial_payment_and_completion(
    client: TestClient,
    db_session: Session,
) -> None:
    user = _make_user(db_session)
    contact_id = _create_contact(client)
    service = AgreementService(db_session)
    agreement = service.create(
        contact_id=contact_id,
        invoice_id=None,
        total_amount=Decimal("300000.00"),
        installments=2,
        start_date=date(2026, 11, 1),
        created_by=user.id,
    )
    first = agreement.installment_items[0]

    partial = service.register_installment_payment(
        agreement_id=agreement.id,
        installment_id=first.id,
        amount=Decimal("50000.00"),
        paid_by=user.id,
    )
    first_after = next(item for item in partial.installment_items if item.id == first.id)
    assert _money(first_after.paid_amount) == _money("50000.00")
    assert first_after.paid_at is None
    assert partial.status is AgreementStatus.ACTIVE

    for item in partial.installment_items:
        service.register_installment_payment(
            agreement_id=agreement.id,
            installment_id=item.id,
            amount=_money(item.amount - item.paid_amount),
            paid_by=user.id,
        )

    completed = service.get(agreement.id)
    assert completed.status is AgreementStatus.COMPLETED
    assert _money(completed.paid_total) == _money("300000.00")
    assert _money(completed.balance) == _money("0.00")


def test_agreement_cannot_exceed_invoice_balance(
    client: TestClient,
    db_session: Session,
) -> None:
    user = _make_user(db_session)
    contact_id, item_id = _setup_catalog(client)
    invoice = _create_issued_invoice(
        client,
        contact_id=contact_id,
        item_id=item_id,
        total="100000.00",
    )

    with pytest.raises(AgreementValidationError):
        AgreementService(db_session).create(
            contact_id=contact_id,
            invoice_id=invoice["id"],
            total_amount=Decimal("100000.01"),
            installments=2,
            start_date=date(2026, 11, 1),
            created_by=user.id,
        )


def test_cancel_keeps_registered_payments(
    client: TestClient,
    db_session: Session,
) -> None:
    user = _make_user(db_session)
    contact_id = _create_contact(client)
    service = AgreementService(db_session)
    agreement = service.create(
        contact_id=contact_id,
        invoice_id=None,
        total_amount=Decimal("200000.00"),
        installments=2,
        start_date=date(2026, 11, 1),
        created_by=user.id,
    )
    first = agreement.installment_items[0]
    service.register_installment_payment(
        agreement_id=agreement.id,
        installment_id=first.id,
        amount=Decimal("25000.00"),
        paid_by=user.id,
    )

    cancelled = service.cancel(agreement.id)
    assert cancelled.status is AgreementStatus.CANCELLED
    assert _money(cancelled.paid_total) == _money("25000.00")
    assert _money(cancelled.balance) == _money("175000.00")
