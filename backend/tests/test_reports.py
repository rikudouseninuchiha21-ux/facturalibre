"""Tests de exportación de reportes a CSV."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from typing import Any
from uuid import uuid4

from fastapi.testclient import TestClient

TWOPLACES = Decimal("0.01")


def _money(value: object) -> Decimal:
    return Decimal(str(value)).quantize(TWOPLACES)


def _setup_reports_data(client: TestClient) -> dict[str, Any]:
    """Crea una factura emitida con un pago y devuelve sus datos clave."""
    contact = client.post(
        "/api/v1/contacts",
        json={"name": "Cliente Reporte", "email": "reporte@example.com"},
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
            "name": "Producto Reporte",
            "description": "Producto Reporte",
            "unit_price": "100.00",
            "tax_id": str(tax["id"]),
        },
    )
    assert item.status_code == 201, item.text
    item = item.json()

    warehouse = client.post(
        "/api/v1/warehouses",
        json={"name": "Bodega Reporte", "code": "REPORTE"},
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

    payment = client.post(
        f"/api/v1/invoices/{invoice['id']}/payments",
        json={
            "amount": "60.00",
            "payment_date": today,
            "method": "Transferencia",
        },
        headers={"Idempotency-Key": str(uuid4())},
    )
    assert payment.status_code == 201, payment.text

    fetched = client.get(f"/api/v1/invoices/{invoice['id']}")
    assert fetched.status_code == 200, fetched.text
    invoice_data = fetched.json()

    return {
        "contact_name": contact["name"],
        "invoice_number": issued.json()["number"],
        "invoice_id": str(invoice["id"]),
        "issue_date": today,
        "subtotal": invoice_data["subtotal"],
        "tax_total": invoice_data["tax_total"],
        "total": invoice_data["total"],
    }


def test_export_invoices_csv(client: TestClient) -> None:
    data = _setup_reports_data(client)

    response = client.get("/api/v1/reports/invoices.csv")

    assert response.status_code == 200, response.text
    assert "text/csv" in response.headers["content-type"]

    body = response.content.decode("utf-8-sig")
    assert "Número,Fecha Emisión,Cliente,Subtotal,Impuestos,Total,Estado" in body
    assert data["invoice_number"] in body
    assert data["contact_name"] in body
    assert data["issue_date"] in body
    assert data["subtotal"] in body
    assert data["tax_total"] in body
    assert data["total"] in body
    assert "Emitida" in body


def test_export_payments_csv(client: TestClient) -> None:
    data = _setup_reports_data(client)

    response = client.get("/api/v1/reports/payments.csv")

    assert response.status_code == 200, response.text
    assert "text/csv" in response.headers["content-type"]

    body = response.content.decode("utf-8-sig")
    assert "Factura,Fecha Pago,Monto,Método" in body
    assert data["invoice_number"] in body
    assert data["issue_date"] in body
    assert "60.00" in body
    assert "Transferencia" in body


def test_export_csv_requires_authentication(
    anonymous_client: TestClient,
) -> None:
    assert anonymous_client.get("/api/v1/reports/invoices.csv").status_code == 401
    assert anonymous_client.get("/api/v1/reports/payments.csv").status_code == 401
