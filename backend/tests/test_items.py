"""Tests CRUD de ítems."""

from decimal import Decimal
from uuid import uuid4

from fastapi.testclient import TestClient


def _create_tax(client: TestClient, name: str = "IVA 19 %") -> dict[str, object]:
    response = client.post(
        "/api/v1/taxes",
        json={"name": name, "rate": "19.0000"},
    )
    assert response.status_code == 201, response.text
    return response.json()


def _create_item(
    client: TestClient,
    *,
    tax_id: str | None = None,
    name: str = "Producto Uno",
) -> dict[str, object]:
    payload = {
        "name": name,
        "description": "Producto de prueba",
        "unit_price": "1250.50",
        "tax_id": tax_id,
    }
    response = client.post("/api/v1/items", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def test_create_get_list_and_tax_validation(client: TestClient) -> None:
    tax = _create_tax(client)
    created = _create_item(client, tax_id=str(tax["id"]))
    item_id = str(created["id"])

    assert created["version"] == 1
    assert Decimal(str(created["unit_price"])) == Decimal("1250.50")
    assert created["tax_id"] == tax["id"]

    get_response = client.get(f"/api/v1/items/{item_id}")
    assert get_response.status_code == 200
    assert get_response.json()["id"] == item_id

    list_response = client.get("/api/v1/items?limit=1&offset=0")
    assert list_response.status_code == 200
    assert len(list_response.json()) == 1
    assert client.get("/api/v1/items?limit=101").status_code == 422

    invalid_tax = client.post(
        "/api/v1/items",
        json={
            "name": "Producto sin impuesto válido",
            "unit_price": "10.00",
            "tax_id": str(uuid4()),
        },
    )
    assert invalid_tax.status_code == 422


def test_update_with_optimistic_locking(client: TestClient) -> None:
    created = _create_item(client)
    item_id = str(created["id"])

    updated = client.patch(
        f"/api/v1/items/{item_id}",
        json={"name": "Producto Actualizado", "unit_price": "999.99", "version": 1},
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["name"] == "Producto Actualizado"
    assert Decimal(str(updated.json()["unit_price"])) == Decimal("999.99")
    assert updated.json()["version"] == 2

    stale = client.patch(
        f"/api/v1/items/{item_id}",
        json={"name": "Versión vieja", "version": 1},
    )
    assert stale.status_code == 409

    assert client.patch(f"/api/v1/items/{item_id}", json={"version": 2}).status_code == 422


def test_soft_delete_excludes_item(client: TestClient) -> None:
    first = _create_item(client, name="Producto A")
    second = _create_item(client, name="Producto B")
    first_id = str(first["id"])
    second_id = str(second["id"])

    deleted = client.delete(f"/api/v1/items/{first_id}")
    assert deleted.status_code == 204

    assert client.get(f"/api/v1/items/{first_id}").status_code == 404
    assert client.delete(f"/api/v1/items/{first_id}").status_code == 404

    listed_ids = {str(item["id"]) for item in client.get("/api/v1/items").json()}
    assert second_id in listed_ids
    assert first_id not in listed_ids
