"""Integración: la compra propaga su centro de costo a las líneas del asiento."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any
from uuid import uuid4

from fastapi.testclient import TestClient


def _create_cost_center(client: TestClient, code: str) -> str:
    response = client.post(
        "/api/v1/cost-centers",
        json={"code": code, "name": "Producción"},
    )
    assert response.status_code == 201, response.text
    return str(response.json()["id"])


def _create_issued_purchase(
    client: TestClient,
    cost_center_id: str | None,
) -> dict[str, Any]:
    supplier = client.post(
        "/api/v1/contacts",
        json={"name": "Proveedor CC", "email": "cc@example.com", "type": "supplier"},
    )
    assert supplier.status_code == 201, supplier.text

    item = client.post(
        "/api/v1/items",
        json={"name": "Producto CC", "description": "Producto CC", "unit_price": "100.00"},
    )
    assert item.status_code == 201, item.text

    warehouse = client.post(
        "/api/v1/warehouses",
        json={"name": "Bodega CC", "code": "CC-BS"},
    )
    assert warehouse.status_code == 201, warehouse.text

    payload: dict[str, object] = {
        "supplier_id": supplier.json()["id"],
        "issue_date": date.today().isoformat(),
        "due_date": (date.today() + timedelta(days=30)).isoformat(),
        "lines": [
            {
                "item_id": item.json()["id"],
                "description": "Producto CC",
                "quantity": "1",
                "unit_cost": "100.00",
                "tax_rate": "0",
            }
        ],
    }
    if cost_center_id is not None:
        payload["cost_center_id"] = cost_center_id

    purchase = client.post(
        "/api/v1/purchases",
        json=payload,
        headers={"Idempotency-Key": str(uuid4())},
    )
    assert purchase.status_code == 201, purchase.text
    assert purchase.json()["cost_center_id"] == cost_center_id

    issued = client.post(f"/api/v1/purchases/{purchase.json()['id']}/issue")
    assert issued.status_code == 200, issued.text
    return issued.json()


def _purchase_entry(client: TestClient, purchase: dict[str, Any]) -> dict[str, Any]:
    entries = client.get("/api/v1/accounting/entries?limit=100")
    assert entries.status_code == 200, entries.text
    matches = [
        entry
        for entry in entries.json()
        if entry["source_type"] == "PURCHASE" and entry["source_id"] == purchase["id"]
    ]
    assert len(matches) == 1
    return matches[0]


def test_purchase_propagates_cost_center_to_entry_lines(client: TestClient) -> None:
    cost_center_id = _create_cost_center(client, f"CC-{uuid4().hex[:6].upper()}")
    purchase = _create_issued_purchase(client, cost_center_id)

    entry = _purchase_entry(client, purchase)
    assert len(entry["lines"]) == 2
    for line in entry["lines"]:
        assert line["cost_center_id"] == cost_center_id

    accounts = {line["account_code"] for line in entry["lines"]}
    assert accounts == {"1435", "220505"}


def test_purchase_without_cost_center_keeps_null(client: TestClient) -> None:
    purchase = _create_issued_purchase(client, None)

    entry = _purchase_entry(client, purchase)
    for line in entry["lines"]:
        assert line["cost_center_id"] is None


def test_purchase_with_invalid_cost_center_returns_422(client: TestClient) -> None:
    supplier = client.post(
        "/api/v1/contacts",
        json={"name": "Proveedor CC2", "email": "cc2@example.com", "type": "supplier"},
    )
    assert supplier.status_code == 201, supplier.text

    response = client.post(
        "/api/v1/purchases",
        json={
            "supplier_id": supplier.json()["id"],
            "issue_date": date.today().isoformat(),
            "due_date": (date.today() + timedelta(days=30)).isoformat(),
            "cost_center_id": str(uuid4()),
            "lines": [
                {
                    "description": "Servicio",
                    "quantity": "1",
                    "unit_cost": "10.00",
                    "tax_rate": "0",
                }
            ],
        },
        headers={"Idempotency-Key": str(uuid4())},
    )
    assert response.status_code == 422, response.text
    assert "cost_center_id" in response.json()["detail"]
