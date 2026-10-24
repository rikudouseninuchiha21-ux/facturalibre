"""Tests de pagos a compras (Cuentas por Pagar)."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from typing import Any
from uuid import uuid4

from fastapi.testclient import TestClient

TWOPLACES = Decimal("0.01")


def _money(value: object) -> Decimal:
    return Decimal(str(value)).quantize(TWOPLACES)


def _setup_purchase_data(client: TestClient) -> dict[str, Any]:
    """Crea un contacto proveedor, ítem, bodega con stock y factura de compra emitida."""
    contact = client.post(
        "/api/v1/contacts",
        json={"name": "Proveedor Pago", "email": "pago@example.com", "type": "supplier"},
    )
    assert contact.status_code == 201, contact.text
    contact = contact.json()

    item = client.post(
        "/api/v1/items",
        json={"name": "Producto Pago", "description": "Producto Pago", "unit_price": "100.00"},
    )
    assert item.status_code == 201, item.text
    item = item.json()

    warehouse = client.post(
        "/api/v1/warehouses",
        json={"name": "Bodega Pago", "code": "PAGO"},
    )
    assert warehouse.status_code == 201, warehouse.text
    warehouse = warehouse.json()

    client.post(
        "/api/v1/inventory/movements",
        json={
            "item_id": str(item["id"]),
            "warehouse_id": warehouse["id"],
            "movement_type": "IN",
            "quantity": "20",
        },
    )

    today = date.today().isoformat()
    due_date = (date.today() + timedelta(days=30)).isoformat()

    invoice = client.post(
        "/api/v1/purchases",
        json={
            "supplier_id": str(contact["id"]),
            "issue_date": today,
            "due_date": due_date,
            "lines": [
                {
                    "item_id": str(item["id"]),
                    "description": "Producto Pago",
                    "quantity": "2",
                    "unit_cost": "100.00",
                    "tax_rate": "19",
                }
            ],
        },
        headers={"Idempotency-Key": str(uuid4())},
    )
    assert invoice.status_code == 201, invoice.text

    issued = client.post(f"/api/v1/purchases/{invoice.json()['id']}/issue")
    assert issued.status_code == 200, issued.text

    fetched = client.get(f"/api/v1/purchases/{invoice.json()['id']}")
    assert fetched.status_code == 200, fetched.text
    invoice_data = fetched.json()

    return {
        "invoice_id": str(invoice.json()["id"]),
        "invoice_number": issued.json()["number"],
        "total": invoice_data["total"],
        "balance": invoice_data["balance"],
    }


def test_register_partial_payment_updates_balance(
    client: TestClient,
) -> None:
    data = _setup_purchase_data(client)
    invoice_id = data["invoice_id"]
    total = _money(data["total"])

    response = client.post(
        f"/api/v1/purchases/{invoice_id}/payments",
        json={
            "amount": "60.00",
            "payment_date": date.today().isoformat(),
            "method": "Transferencia",
        },
        headers={"Idempotency-Key": str(uuid4())},
    )
    assert response.status_code == 201, response.text
    payment = response.json()
    assert _money(payment["amount"]) == Decimal("60.00")
    assert payment["method"] == "Transferencia"

    fetched = client.get(f"/api/v1/purchases/{invoice_id}")
    assert fetched.status_code == 200, fetched.text
    updated = fetched.json()
    assert _money(updated["balance"]) == total - Decimal("60.00")


def test_register_full_payment_sets_balance_to_zero(
    client: TestClient,
) -> None:
    data = _setup_purchase_data(client)
    invoice_id = data["invoice_id"]
    total = data["total"]

    response = client.post(
        f"/api/v1/purchases/{invoice_id}/payments",
        json={
            "amount": total,
            "payment_date": date.today().isoformat(),
            "method": "Efectivo",
        },
        headers={"Idempotency-Key": str(uuid4())},
    )
    assert response.status_code == 201, response.text

    fetched = client.get(f"/api/v1/purchases/{invoice_id}")
    assert fetched.status_code == 200, fetched.text
    updated = fetched.json()
    assert _money(updated["balance"]) == Decimal("0.00")


def test_register_payment_generates_accounting_entry(
    client: TestClient,
) -> None:
    data = _setup_purchase_data(client)
    invoice_id = data["invoice_id"]

    payment_response = client.post(
        f"/api/v1/purchases/{invoice_id}/payments",
        json={
            "amount": "40.00",
            "payment_date": date.today().isoformat(),
            "method": "Transferencia",
        },
        headers={"Idempotency-Key": str(uuid4())},
    )
    assert payment_response.status_code == 201, payment_response.text
    payment_id = payment_response.json()["id"]

    entries = client.get("/api/v1/accounting/entries")
    assert entries.status_code == 200, entries.text

    purchase_payment_entries = [
        e
        for e in entries.json()
        if e["source_type"] == "PURCHASE_PAYMENT"
        and e["source_id"] == payment_id
    ]
    assert len(purchase_payment_entries) == 1
    entry = purchase_payment_entries[0]
    assert _money(entry["total_debit"]) == Decimal("40.00")
    assert _money(entry["total_credit"]) == Decimal("40.00")


def test_rejects_payment_on_draft_purchase(
    client: TestClient,
) -> None:
    contact = client.post(
        "/api/v1/contacts",
        json={"name": "Proveedor Draft", "email": "draft@example.com", "type": "supplier"},
    )
    assert contact.status_code == 201, contact.text
    contact = contact.json()

    item = client.post(
        "/api/v1/items",
        json={"name": "Ítem Draft", "description": "Ítem Draft", "unit_price": "50.00"},
    )
    assert item.status_code == 201, item.text
    item = item.json()

    invoice = client.post(
        "/api/v1/purchases",
        json={
            "supplier_id": str(contact["id"]),
            "issue_date": date.today().isoformat(),
            "due_date": (date.today() + timedelta(days=30)).isoformat(),
            "lines": [
                {
                    "item_id": str(item["id"]),
                    "description": "Ítem Draft",
                    "quantity": "1",
                    "unit_cost": "50.00",
                    "tax_rate": "0",
                }
            ],
        },
        headers={"Idempotency-Key": str(uuid4())},
    )
    assert invoice.status_code == 201, invoice.text
    # Factura en DRAFT, no se puede pagar
    response = client.post(
        f"/api/v1/purchases/{invoice.json()['id']}/payments",
        json={
            "amount": "25.00",
            "payment_date": date.today().isoformat(),
            "method": "Transferencia",
        },
        headers={"Idempotency-Key": str(uuid4())},
    )
    assert response.status_code == 409, response.text


def test_rejects_overpayment(
    client: TestClient,
) -> None:
    data = _setup_purchase_data(client)
    invoice_id = data["invoice_id"]
    total = data["total"]

    response = client.post(
        f"/api/v1/purchases/{invoice_id}/payments",
        json={
            "amount": str(_money(total) + Decimal("10.00")),
            "payment_date": date.today().isoformat(),
            "method": "Transferencia",
        },
        headers={"Idempotency-Key": str(uuid4())},
    )
    assert response.status_code == 422, response.text


def test_purchase_payments_requires_authentication(
    anonymous_client: TestClient,
) -> None:
    assert (
        anonymous_client.post(
            "/api/v1/purchases/00000000-0000-0000-0000-000000000000/payments",
            json={"amount": "10.00", "payment_date": date.today().isoformat(), "method": "Efectivo"},
        ).status_code
        == 401
    )
    assert (
        anonymous_client.get(
            "/api/v1/purchases/00000000-0000-0000-0000-000000000000/payments"
        ).status_code
        == 401
    )
