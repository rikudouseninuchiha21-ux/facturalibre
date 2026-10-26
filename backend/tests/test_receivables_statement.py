"""Tests del estado de cuenta por cliente."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.domain.models.credit_note import CreditNote, CreditNoteStatus

TWOPLACES = Decimal("0.01")


def _money(value: object) -> Decimal:
    return Decimal(str(value)).quantize(TWOPLACES)


def _setup_catalog(client: TestClient) -> tuple[str, str]:
    suffix = uuid4().hex[:8].upper()
    contact = client.post(
        "/api/v1/contacts",
        json={"name": f"Cliente Estado {suffix}", "email": f"estado-{suffix}@example.com"},
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
    return str(contact.json()["id"]), str(item.json()["id"])


def _create_issued_invoice(
    client: TestClient,
    *,
    contact_id: str,
    item_id: str,
    total: str,
    issue_date: date,
    due_date: date,
) -> dict[str, Any]:
    response = client.post(
        "/api/v1/invoices",
        json={
            "contact_id": contact_id,
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


def _pay(
    client: TestClient,
    *,
    invoice_id: str,
    amount: str,
    payment_date: date,
) -> None:
    response = client.post(
        f"/api/v1/invoices/{invoice_id}/payments",
        json={
            "amount": amount,
            "payment_date": payment_date.isoformat(),
            "method": "Transferencia",
        },
        headers={"Idempotency-Key": str(uuid4())},
    )
    assert response.status_code == 201, response.text


def _add_credit_note(
    db_session: Session,
    *,
    invoice_id: str,
    total: str,
    issue_date: date,
    number: str,
) -> None:
    db_session.add(
        CreditNote(
            invoice_id=invoice_id,
            number=number,
            issue_date=issue_date,
            status=CreditNoteStatus.ISSUED,
            subtotal=Decimal(total),
            tax_total=Decimal("0.00"),
            total=Decimal(total),
        )
    )
    db_session.flush()


def _statement(
    client: TestClient,
    *,
    contact_id: str,
    from_date: date,
    to_date: date,
) -> dict[str, Any]:
    response = client.get(
        f"/api/v1/receivables/customers/{contact_id}/statement",
        params={"from_date": from_date.isoformat(), "to_date": to_date.isoformat()},
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_statement_with_opening_invoice_payment_and_credit_note(
    client: TestClient,
    db_session: Session,
) -> None:
    contact_id, item_id = _setup_catalog(client)
    _create_issued_invoice(
        client,
        contact_id=contact_id,
        item_id=item_id,
        total="100000.00",
        issue_date=date(2026, 1, 10),
        due_date=date(2026, 2, 9),
    )
    second = _create_issued_invoice(
        client,
        contact_id=contact_id,
        item_id=item_id,
        total="200000.00",
        issue_date=date(2026, 2, 10),
        due_date=date(2026, 3, 12),
    )
    _pay(
        client,
        invoice_id=str(second["id"]),
        amount="50000.00",
        payment_date=date(2026, 2, 15),
    )
    _add_credit_note(
        db_session,
        invoice_id=str(second["id"]),
        total="30000.00",
        issue_date=date(2026, 2, 20),
        number="NC-ESTADO-1",
    )

    statement = _statement(
        client,
        contact_id=contact_id,
        from_date=date(2026, 2, 1),
        to_date=date(2026, 2, 28),
    )

    assert _money(statement["opening_balance"]) == _money("100000.00")
    assert _money(statement["closing_balance"]) == _money("220000.00")
    assert [line["type"] for line in statement["lines"]] == [
        "INVOICE",
        "PAYMENT",
        "CREDIT_NOTE",
    ]
    assert _money(statement["lines"][0]["debit"]) == _money("200000.00")
    assert _money(statement["lines"][1]["credit"]) == _money("50000.00")
    assert _money(statement["lines"][2]["credit"]) == _money("30000.00")
    assert _money(statement["lines"][-1]["running_balance"]) == _money("220000.00")


def test_statement_empty_range_keeps_opening_and_closing(
    client: TestClient,
) -> None:
    contact_id, item_id = _setup_catalog(client)
    _create_issued_invoice(
        client,
        contact_id=contact_id,
        item_id=item_id,
        total="75000.00",
        issue_date=date(2026, 1, 5),
        due_date=date(2026, 2, 4),
    )

    statement = _statement(
        client,
        contact_id=contact_id,
        from_date=date(2026, 3, 1),
        to_date=date(2026, 3, 31),
    )

    assert statement["lines"] == []
    assert _money(statement["opening_balance"]) == _money("75000.00")
    assert _money(statement["closing_balance"]) == _money("75000.00")


def test_statement_running_balance_per_line(client: TestClient) -> None:
    contact_id, item_id = _setup_catalog(client)
    invoice = _create_issued_invoice(
        client,
        contact_id=contact_id,
        item_id=item_id,
        total="100000.00",
        issue_date=date(2026, 2, 1),
        due_date=date(2026, 3, 3),
    )
    _pay(
        client,
        invoice_id=str(invoice["id"]),
        amount="40000.00",
        payment_date=date(2026, 2, 5),
    )
    _pay(
        client,
        invoice_id=str(invoice["id"]),
        amount="10000.00",
        payment_date=date(2026, 2, 10),
    )

    statement = _statement(
        client,
        contact_id=contact_id,
        from_date=date(2026, 2, 1),
        to_date=date(2026, 2, 28),
    )

    balances = [_money(line["running_balance"]) for line in statement["lines"]]
    assert balances == [
        _money("100000.00"),
        _money("60000.00"),
        _money("50000.00"),
    ]
    assert _money(statement["closing_balance"]) == _money("50000.00")
