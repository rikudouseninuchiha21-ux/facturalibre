"""Tests de notas crédito para facturas de venta."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from typing import Any
from uuid import uuid4

from fastapi.testclient import TestClient

TWOPLACES = Decimal("0.01")


def _money(value: object) -> Decimal:
    return Decimal(str(value)).quantize(TWOPLACES)


def _setup_invoice_for_credit_note(client: TestClient) -> dict[str, Any]:
    """Crea un contacto, ítem, bodega con stock y factura emitida con pago."""
    contact = client.post(
        "/api/v1/contacts",
        json={"name": "Cliente Crédito", "email": "credito@example.com"},
    )
    assert contact.status_code == 201, contact.text
    contact = contact.json()

    tax = client.post(
        "/api/v1/taxes",
        json={"name": "IVA 19 %", "rate": "19.0000"},
    )
    assert tax.status_code == 201, tax.text
    tax = tax.json()

    item = client.post(
        "/api/v1/items",
        json={
            "name": "Producto Crédito",
            "description": "Producto Crédito",
            "unit_price": "100.00",
            "tax_id": str(tax["id"]),
        },
    )
    assert item.status_code == 201, item.text
    item = item.json()

    warehouse = client.post(
        "/api/v1/warehouses",
        json={"name": "Bodega Crédito", "code": "CREDITO"},
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
        "/api/v1/invoices",
        json={
            "contact_id": str(contact["id"]),
            "issue_date": today,
            "due_date": due_date,
            "currency": "COP",
            "lines": [
                {
                    "item_id": str(item["id"]),
                    "quantity": "2",
                    "unit_price": "100.00",
                    "discount_percent": "0",
                    "tax_rate": "19",
                }
            ],
        },
        headers={"Idempotency-Key": str(uuid4())},
    )
    assert invoice.status_code == 201, invoice.text
    invoice = invoice.json()

    issued = client.post(f"/api/v1/invoices/{invoice['id']}/issue")
    assert issued.status_code == 200, issued.text

    fetched = client.get(f"/api/v1/invoices/{invoice['id']}")
    assert fetched.status_code == 200, fetched.text
    invoice_data = fetched.json()

    return {
        "invoice_id": str(invoice["id"]),
        "invoice_number": issued.json()["number"],
        "item_id": str(item["id"]),
        "invoice_line_id": str(invoice_data["lines"][0]["id"]),
        "total": invoice_data["total"],
        "balance": invoice_data["balance"],
    }


def test_create_credit_note_draft(client: TestClient) -> None:
    data = _setup_invoice_for_credit_note(client)
    invoice_id = data["invoice_id"]
    invoice_line_id = data["invoice_line_id"]

    response = client.post(
        f"/api/v1/invoices/{invoice_id}/credit-notes",
        json={
            "issue_date": date.today().isoformat(),
            "lines": [
                {
                    "invoice_line_id": invoice_line_id,
                    "description": "Devolución producto",
                    "quantity": "1",
                    "unit_price": "100.00",
                    "tax_rate": "19",
                }
            ],
        },
        headers={"Idempotency-Key": str(uuid4())},
    )
    assert response.status_code == 201, response.text
    cn = response.json()
    assert cn["number"] is None  # DRAFT sin número
    assert cn["status"] == "draft"
    assert _money(cn["total"]) == Decimal("119.00")


def test_issue_credit_note_total(client: TestClient) -> None:
    data = _setup_invoice_for_credit_note(client)
    invoice_id = data["invoice_id"]
    invoice_line_id = data["invoice_line_id"]

    # Crear nota crédito por el total
    cn_create = client.post(
        f"/api/v1/invoices/{invoice_id}/credit-notes",
        json={
            "issue_date": date.today().isoformat(),
            "lines": [
                {
                    "invoice_line_id": invoice_line_id,
                    "description": "Devolución total",
                    "quantity": "2",
                    "unit_price": "100.00",
                    "tax_rate": "19",
                }
            ],
        },
        headers={"Idempotency-Key": str(uuid4())},
    )
    assert cn_create.status_code == 201, cn_create.text
    cn_id = cn_create.json()["id"]

    # Emitir nota crédito
    response = client.post(f"/api/v1/invoices/{invoice_id}/credit-notes/{cn_id}/issue")
    assert response.status_code == 200, response.text
    cn = response.json()
    assert cn["number"] is not None
    assert cn["status"] == "issued"

    # Verificar balance de la factura es 0
    fetched = client.get(f"/api/v1/invoices/{invoice_id}")
    assert fetched.status_code == 200, fetched.text
    updated = fetched.json()
    assert _money(updated["balance"]) == Decimal("0.00")


def test_issue_credit_note_partial(client: TestClient) -> None:
    data = _setup_invoice_for_credit_note(client)
    invoice_id = data["invoice_id"]
    invoice_line_id = data["invoice_line_id"]

    # Crear nota crédito parcial (solo 1 de 2 unidades)
    cn_create = client.post(
        f"/api/v1/invoices/{invoice_id}/credit-notes",
        json={
            "issue_date": date.today().isoformat(),
            "lines": [
                {
                    "invoice_line_id": invoice_line_id,
                    "description": "Devolución parcial",
                    "quantity": "1",
                    "unit_price": "100.00",
                    "tax_rate": "19",
                }
            ],
        },
        headers={"Idempotency-Key": str(uuid4())},
    )
    assert cn_create.status_code == 201, cn_create.text
    cn_id = cn_create.json()["id"]

    response = client.post(f"/api/v1/invoices/{invoice_id}/credit-notes/{cn_id}/issue")
    assert response.status_code == 200, response.text

    fetched = client.get(f"/api/v1/invoices/{invoice_id}")
    assert fetched.status_code == 200, fetched.text
    updated = fetched.json()
    # Balance = total - crédito = 238.00 - 119.00 = 119.00
    assert _money(updated["balance"]) == _money(data["total"]) - Decimal("119.00")


def test_reject_quantity_exceeds_original(client: TestClient) -> None:
    data = _setup_invoice_for_credit_note(client)
    invoice_id = data["invoice_id"]
    invoice_line_id = data["invoice_line_id"]

    # Intentar devolver 3 unidades cuando solo hay 2
    response = client.post(
        f"/api/v1/invoices/{invoice_id}/credit-notes",
        json={
            "issue_date": date.today().isoformat(),
            "lines": [
                {
                    "invoice_line_id": invoice_line_id,
                    "description": "Devolución excesiva",
                    "quantity": "3",
                    "unit_price": "100.00",
                    "tax_rate": "19",
                }
            ],
        },
        headers={"Idempotency-Key": str(uuid4())},
    )
    assert response.status_code == 422, response.text


def test_reject_credit_note_on_draft_invoice(client: TestClient) -> None:
    # Crear factura en DRAFT (sin emitir)
    contact = client.post(
        "/api/v1/contacts",
        json={"name": "Cliente Draft", "email": "draft2@example.com"},
    )
    assert contact.status_code == 201, contact.text
    contact = contact.json()

    item = client.post(
        "/api/v1/items",
        json={"name": "Ítem Draft CN", "description": "Ítem Draft CN", "unit_price": "50.00"},
    )
    assert item.status_code == 201, item.text
    item = item.json()

    invoice = client.post(
        "/api/v1/invoices",
        json={
            "contact_id": str(contact["id"]),
            "issue_date": date.today().isoformat(),
            "due_date": (date.today() + timedelta(days=30)).isoformat(),
            "currency": "COP",
            "lines": [
                {
                    "item_id": str(item["id"]),
                    "quantity": "1",
                    "unit_price": "50.00",
                    "discount_percent": "0",
                    "tax_rate": "0",
                }
            ],
        },
        headers={"Idempotency-Key": str(uuid4())},
    )
    assert invoice.status_code == 201, invoice.text
    invoice = invoice.json()

    response = client.post(
        f"/api/v1/invoices/{invoice['id']}/credit-notes",
        json={
            "issue_date": date.today().isoformat(),
            "lines": [
                {
                    "description": "Devolución draft",
                    "quantity": "1",
                    "unit_price": "50.00",
                    "tax_rate": "0",
                }
            ],
        },
        headers={"Idempotency-Key": str(uuid4())},
    )
    assert response.status_code == 422, response.text


def test_credit_note_requires_authentication(
    anonymous_client: TestClient,
) -> None:
    assert (
        anonymous_client.post(
            "/api/v1/invoices/00000000-0000-0000-0000-000000000000/credit-notes",
            json={
                "issue_date": date.today().isoformat(),
                "lines": [
                    {
                        "description": "Devolución",
                        "quantity": "1",
                        "unit_price": "10.00",
                        "tax_rate": "0",
                    }
                ],
            },
        ).status_code
        == 401
    )
