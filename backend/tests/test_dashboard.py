"""Tests de las métricas agregadas del dashboard."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from typing import Any
from uuid import uuid4

from fastapi.testclient import TestClient

TWOPLACES = Decimal("0.01")


def _money(value: object) -> Decimal:
    return Decimal(str(value)).quantize(TWOPLACES)


def _previous_month_start(today: date) -> date:
    if today.month == 1:
        return date(today.year - 1, 12, 1)
    return date(today.year, today.month - 1, 1)


def _setup_catalog(client: TestClient) -> tuple[str, str]:
    contact = client.post(
        "/api/v1/contacts",
        json={"name": "Cliente Dashboard", "email": "dashboard@example.com"},
    )
    assert contact.status_code == 201, contact.text

    item = client.post(
        "/api/v1/items",
        json={
            "name": "Producto dashboard",
            "description": "Producto dashboard",
            "unit_price": "100.00",
            "tax_id": None,
        },
    )
    assert item.status_code == 201, item.text

    warehouse = client.post(
        "/api/v1/warehouses",
        json={"name": "Bodega dashboard", "code": "DASHBOARD"},
    )
    assert warehouse.status_code == 201, warehouse.text

    movement = client.post(
        "/api/v1/inventory/movements",
        json={
            "item_id": item.json()["id"],
            "warehouse_id": warehouse.json()["id"],
            "movement_type": "IN",
            "quantity": "20",
        },
    )
    assert movement.status_code == 201, movement.text
    return str(contact.json()["id"]), str(item.json()["id"])


def _create_invoice(
    client: TestClient,
    *,
    contact_id: str,
    item_id: str,
    total: str,
    issue_date: date,
) -> dict[str, Any]:
    response = client.post(
        "/api/v1/invoices",
        json={
            "contact_id": contact_id,
            "issue_date": issue_date.isoformat(),
            "due_date": (issue_date + timedelta(days=30)).isoformat(),
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
    return response.json()


def _issue(client: TestClient, invoice_id: object) -> dict[str, Any]:
    response = client.post(f"/api/v1/invoices/{invoice_id}/issue")
    assert response.status_code == 200, response.text
    return response.json()


def _void(client: TestClient, invoice_id: object) -> None:
    response = client.post(
        f"/api/v1/invoices/{invoice_id}/void",
        json={"reason": "Factura de prueba"},
    )
    assert response.status_code == 200, response.text


def _pay(client: TestClient, invoice_id: object, amount: str) -> None:
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


def test_dashboard_summary_requires_authentication(
    anonymous_client: TestClient,
) -> None:
    response = anonymous_client.get("/api/v1/dashboard/summary")

    assert response.status_code == 401
    assert response.json() == {"detail": "Sesión no válida o expirada"}


def test_dashboard_summary_aggregates_kpis_and_monthly_sales(
    client: TestClient,
) -> None:
    contact_id, item_id = _setup_catalog(client)
    today = date.today()
    previous_month = _previous_month_start(today)

    draft = _create_invoice(
        client,
        contact_id=contact_id,
        item_id=item_id,
        total="50.00",
        issue_date=today,
    )

    issued = _issue(
        client,
        _create_invoice(
            client,
            contact_id=contact_id,
            item_id=item_id,
            total="100.00",
            issue_date=today,
        )["id"],
    )
    _issue(
        client,
        _create_invoice(
            client,
            contact_id=contact_id,
            item_id=item_id,
            total="40.00",
            issue_date=previous_month,
        )["id"],
    )
    voided = _create_invoice(
        client,
        contact_id=contact_id,
        item_id=item_id,
        total="25.00",
        issue_date=today,
    )
    _issue(client, voided["id"])
    _void(client, voided["id"])

    assert draft["lifecycle_status"] == "draft"
    _pay(client, issued["id"], "30.00")

    response = client.get("/api/v1/dashboard/summary")

    assert response.status_code == 200, response.text
    summary = response.json()

    assert _money(summary["total_revenue"]) == Decimal("30.00")
    assert _money(summary["total_invoiced"]) == Decimal("140.00")
    assert _money(summary["pending_balance"]) == Decimal("110.00")
    assert summary["invoices_by_status"] == {
        "draft": 1,
        "issued": 2,
        "void": 1,
    }

    monthly = summary["monthly_sales"]
    assert len(monthly) == 6
    assert monthly[-1]["month"] == f"{today.year:04d}-{today.month:02d}"
    assert _money(monthly[-1]["total"]) == Decimal("100.00")
    assert monthly[-2]["month"] == f"{previous_month.year:04d}-{previous_month.month:02d}"
    assert _money(monthly[-2]["total"]) == Decimal("40.00")
