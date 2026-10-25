"""Tests del cobro atómico del POS y del asiento de costo de ventas."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from typing import Any
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.application.accounting.service import AccountingError
from app.domain.models.accounting import AccountingAccount, AccountingEntry
from app.domain.models.invoice import Invoice
from app.domain.models.payment import Payment
from app.domain.models.stock import StockBalance, StockMovement, StockMovementType

TWOPLACES = Decimal("0.01")


def _money(value: object) -> Decimal:
    return Decimal(str(value)).quantize(TWOPLACES)


def _setup_pos_data(
    client: TestClient,
    *,
    quantity: str = "10",
    unit_cost: str = "40.00",
) -> dict[str, str]:
    """Crea contacto, ítem y stock valorizado en la bodega PRINCIPAL."""
    contact = client.post(
        "/api/v1/contacts",
        json={"name": "Cliente POS", "email": "pos@example.com"},
    )
    assert contact.status_code == 201, contact.text

    item = client.post(
        "/api/v1/items",
        json={
            "name": "Producto POS",
            "description": "Producto POS",
            "unit_price": "100.00",
            "tax_id": None,
        },
    )
    assert item.status_code == 201, item.text

    warehouse = client.post(
        "/api/v1/warehouses",
        json={"name": "Bodega principal", "code": "PRINCIPAL"},
    )
    assert warehouse.status_code == 201, warehouse.text

    movement = client.post(
        "/api/v1/inventory/movements",
        json={
            "item_id": item.json()["id"],
            "warehouse_id": warehouse.json()["id"],
            "movement_type": "IN",
            "quantity": quantity,
            "unit_cost": unit_cost,
        },
    )
    assert movement.status_code == 201, movement.text

    return {
        "contact_id": str(contact.json()["id"]),
        "item_id": str(item.json()["id"]),
        "warehouse_id": str(warehouse.json()["id"]),
    }


def _add_stock(
    client: TestClient,
    data: dict[str, str],
    *,
    quantity: str,
    unit_cost: str,
) -> None:
    movement = client.post(
        "/api/v1/inventory/movements",
        json={
            "item_id": data["item_id"],
            "warehouse_id": data["warehouse_id"],
            "movement_type": "IN",
            "quantity": quantity,
            "unit_cost": unit_cost,
        },
    )
    assert movement.status_code == 201, movement.text


def _checkout_payload(
    data: dict[str, str],
    *,
    quantity: str = "1",
    unit_price: str = "100.00",
) -> dict[str, Any]:
    today = date.today()
    return {
        "contact_id": data["contact_id"],
        "issue_date": today.isoformat(),
        "due_date": (today + timedelta(days=30)).isoformat(),
        "currency": "COP",
        "lines": [
            {
                "item_id": data["item_id"],
                "quantity": quantity,
                "unit_price": unit_price,
                "discount_percent": "0",
                "tax_rate": "0",
            }
        ],
    }


def _checkout(
    client: TestClient,
    payload: dict[str, Any],
    *,
    key: str | None = None,
) -> Any:
    return client.post(
        "/api/v1/pos/checkout",
        json=payload,
        headers={"Idempotency-Key": key or str(uuid4())},
    )


def _entries(client: TestClient) -> list[dict[str, Any]]:
    response = client.get("/api/v1/accounting/entries?limit=100")
    assert response.status_code == 200, response.text
    return response.json()


def _entry_for(client: TestClient, source_type: str, source_id: str) -> dict[str, Any]:
    matches = [
        entry
        for entry in _entries(client)
        if entry["source_type"] == source_type and entry["source_id"] == source_id
    ]
    assert len(matches) == 1
    return matches[0]


def _lines_by_code(entry: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {str(line["account_code"]): line for line in entry["lines"]}


def _balance(client: TestClient, data: dict[str, str]) -> Decimal:
    response = client.get(
        "/api/v1/inventory/balances",
        params={"warehouse_id": data["warehouse_id"], "item_id": data["item_id"]},
    )
    assert response.status_code == 200, response.text
    balances = response.json()
    assert len(balances) == 1
    return _money(balances[0]["quantity"])


def test_pos_checkout_registers_cash_payment_and_cogs(client: TestClient) -> None:
    data = _setup_pos_data(client)
    payload = _checkout_payload(data)

    response = _checkout(client, payload)

    assert response.status_code == 201, response.text
    result = response.json()
    invoice = result["invoice"]
    payment = result["payment"]
    assert invoice["lifecycle_status"] == "issued"
    assert invoice["payment_status"] == "paid"
    assert _money(invoice["balance"]) == Decimal("0.00")
    assert invoice["number"] is not None
    assert payment is not None
    assert payment["invoice_id"] == invoice["id"]
    assert _money(payment["amount"]) == Decimal("100.00")
    assert payment["method"] == "cash"

    listed = client.get(f"/api/v1/invoices/{invoice['id']}/payments")
    assert listed.status_code == 200, listed.text
    assert [item["id"] for item in listed.json()] == [payment["id"]]

    assert _balance(client, data) == Decimal("9.00")

    invoice_entry = _entry_for(client, "INVOICE", invoice["id"])
    invoice_lines = _lines_by_code(invoice_entry)
    assert _money(invoice_lines["130505"]["debit"]) == Decimal("100.00")
    assert _money(invoice_lines["413505"]["credit"]) == Decimal("100.00")
    assert _money(invoice_lines["6135"]["debit"]) == Decimal("40.00")
    assert _money(invoice_lines["1435"]["credit"]) == Decimal("40.00")
    assert _money(invoice_entry["total_debit"]) == Decimal("140.00")
    assert _money(invoice_entry["total_credit"]) == Decimal("140.00")

    payment_entry = _entry_for(client, "PAYMENT", payment["id"])
    payment_lines = _lines_by_code(payment_entry)
    assert _money(payment_lines["110505"]["debit"]) == Decimal("100.00")
    assert _money(payment_lines["130505"]["credit"]) == Decimal("100.00")


def test_pos_checkout_uses_weighted_average_cost(client: TestClient) -> None:
    data = _setup_pos_data(client, quantity="10", unit_cost="40.00")
    _add_stock(client, data, quantity="10", unit_cost="60.00")
    payload = _checkout_payload(data, quantity="2", unit_price="100.00")

    response = _checkout(client, payload)

    assert response.status_code == 201, response.text
    invoice = response.json()["invoice"]
    assert _money(invoice["total"]) == Decimal("200.00")
    assert _balance(client, data) == Decimal("18.00")

    entry = _entry_for(client, "INVOICE", invoice["id"])
    lines = _lines_by_code(entry)
    # (10 * 40 + 10 * 60) / 20 = 50 por unidad; 2 unidades = 100 de COGS.
    assert _money(lines["6135"]["debit"]) == Decimal("100.00")
    assert _money(lines["1435"]["credit"]) == Decimal("100.00")


def test_pos_checkout_is_idempotent(client: TestClient, db_session: Session) -> None:
    data = _setup_pos_data(client)
    payload = _checkout_payload(data)
    key = str(uuid4())

    first = _checkout(client, payload, key=key)
    second = _checkout(client, payload, key=key)

    assert first.status_code == 201, first.text
    assert second.status_code == 201, second.text
    assert second.json()["invoice"]["id"] == first.json()["invoice"]["id"]
    assert second.json()["payment"]["id"] == first.json()["payment"]["id"]
    assert _balance(client, data) == Decimal("9.00")
    assert db_session.scalar(select(func.count()).select_from(Invoice)) == 1
    assert db_session.scalar(select(func.count()).select_from(Payment)) == 1
    assert db_session.scalar(select(func.count()).select_from(AccountingEntry)) == 2


def test_pos_checkout_rejects_same_key_with_different_body(client: TestClient) -> None:
    data = _setup_pos_data(client)
    payload = _checkout_payload(data)
    key = str(uuid4())

    first = _checkout(client, payload, key=key)
    assert first.status_code == 201, first.text

    changed = _checkout_payload(data, quantity="2")
    response = _checkout(client, changed, key=key)

    assert response.status_code == 409
    assert response.json() == {"detail": "Idempotency-Key reutilizada con body diferente"}
    assert _balance(client, data) == Decimal("9.00")


def test_pos_checkout_is_atomic_if_cogs_accounting_fails(
    client: TestClient,
    db_session: Session,
) -> None:
    data = _setup_pos_data(client)
    db_session.execute(delete(AccountingAccount).where(AccountingAccount.code == "6135"))
    db_session.flush()

    with pytest.raises(AccountingError):
        _checkout(client, _checkout_payload(data))

    assert db_session.scalar(select(func.count()).select_from(Invoice)) == 0
    assert db_session.scalar(select(func.count()).select_from(Payment)) == 0
    assert db_session.scalar(select(func.count()).select_from(AccountingEntry)) == 0
    assert _balance(client, data) == Decimal("10.00")
    assert (
        db_session.scalar(
            select(func.count())
            .select_from(StockMovement)
            .where(StockMovement.movement_type == StockMovementType.OUT)
        )
        == 0
    )


def test_normal_invoice_issue_generates_cogs_without_auto_payment(
    client: TestClient,
    db_session: Session,
) -> None:
    data = _setup_pos_data(client)
    payload = _checkout_payload(data)

    created = client.post(
        "/api/v1/invoices",
        json=payload,
        headers={"Idempotency-Key": str(uuid4())},
    )
    assert created.status_code == 201, created.text
    invoice_id = created.json()["id"]

    issued = client.post(f"/api/v1/invoices/{invoice_id}/issue")
    assert issued.status_code == 200, issued.text
    invoice = issued.json()
    assert invoice["payment_status"] == "unpaid"
    assert _money(invoice["balance"]) == Decimal("100.00")
    assert client.get(f"/api/v1/invoices/{invoice_id}/payments").json() == []
    assert db_session.scalar(select(func.count()).select_from(Payment)) == 0

    entry = _entry_for(client, "INVOICE", invoice_id)
    lines = _lines_by_code(entry)
    assert _money(lines["6135"]["debit"]) == Decimal("40.00")
    assert _money(lines["1435"]["credit"]) == Decimal("40.00")

    out_movement = db_session.scalar(
        select(StockMovement).where(StockMovement.movement_type == StockMovementType.OUT)
    )
    assert out_movement is not None
    assert _money(out_movement.unit_cost) == Decimal("40.00")
    assert db_session.scalar(select(func.count()).select_from(StockBalance)) == 1
