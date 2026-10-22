"""Tests CRUD de impuestos."""

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


def test_create_get_list_and_validation(client: TestClient) -> None:
    created = _create_tax(client)
    tax_id = str(created["id"])

    assert created["version"] == 1
    assert Decimal(str(created["rate"])) == Decimal("19.0000")

    get_response = client.get(f"/api/v1/taxes/{tax_id}")
    assert get_response.status_code == 200
    assert get_response.json()["id"] == tax_id

    list_response = client.get("/api/v1/taxes?limit=1&offset=0")
    assert list_response.status_code == 200
    assert len(list_response.json()) == 1
    assert client.get("/api/v1/taxes?limit=101").status_code == 422
    assert client.get(f"/api/v1/taxes/{uuid4()}").status_code == 404

    invalid_rate = client.post(
        "/api/v1/taxes",
        json={"name": "Tarifa inválida", "rate": "100.0001"},
    )
    assert invalid_rate.status_code == 422


def test_update_with_optimistic_locking(client: TestClient) -> None:
    created = _create_tax(client)
    tax_id = str(created["id"])

    updated = client.patch(
        f"/api/v1/taxes/{tax_id}",
        json={"name": "IVA actualizado", "rate": "19.5000", "version": 1},
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["name"] == "IVA actualizado"
    assert Decimal(str(updated.json()["rate"])) == Decimal("19.5000")
    assert updated.json()["version"] == 2

    stale = client.patch(
        f"/api/v1/taxes/{tax_id}",
        json={"name": "Versión vieja", "version": 1},
    )
    assert stale.status_code == 409

    empty_update = client.patch(
        f"/api/v1/taxes/{tax_id}",
        json={"version": 2},
    )
    assert empty_update.status_code == 422


def test_soft_delete_excludes_tax(client: TestClient) -> None:
    first = _create_tax(client, name="IVA A")
    second = _create_tax(client, name="IVA B")
    first_id = str(first["id"])
    second_id = str(second["id"])

    deleted = client.delete(f"/api/v1/taxes/{first_id}")
    assert deleted.status_code == 204

    assert client.get(f"/api/v1/taxes/{first_id}").status_code == 404
    assert client.delete(f"/api/v1/taxes/{first_id}").status_code == 404

    listed_ids = {str(tax["id"]) for tax in client.get("/api/v1/taxes").json()}
    assert second_id in listed_ids
    assert first_id not in listed_ids
