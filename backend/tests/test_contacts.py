"""Tests CRUD de contactos."""

from uuid import uuid4

from fastapi.testclient import TestClient


def _create_contact(client: TestClient, **overrides: object) -> dict[str, object]:
    payload = {
        "name": "Cliente Uno",
        "email": "cliente1@example.com",
        "tax_id": "900123456",
        **overrides,
    }
    response = client.post("/api/v1/contacts", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def test_create_get_list_and_validation(client: TestClient) -> None:
    created = _create_contact(client)
    contact_id = str(created["id"])

    assert created["version"] == 1
    assert created["email"] == "cliente1@example.com"

    get_response = client.get(f"/api/v1/contacts/{contact_id}")
    assert get_response.status_code == 200
    assert get_response.json()["id"] == contact_id

    list_response = client.get("/api/v1/contacts?limit=1&offset=0")
    assert list_response.status_code == 200
    assert len(list_response.json()) == 1

    assert client.get("/api/v1/contacts?limit=101").status_code == 422
    assert client.get("/api/v1/contacts?limit=0").status_code == 422
    assert client.get(f"/api/v1/contacts/{uuid4()}").status_code == 404

    invalid_email = client.post(
        "/api/v1/contacts",
        json={"name": "Inválido", "email": "no-es-un-email"},
    )
    assert invalid_email.status_code == 422


def test_update_with_optimistic_locking(client: TestClient) -> None:
    created = _create_contact(client)
    contact_id = str(created["id"])

    updated = client.patch(
        f"/api/v1/contacts/{contact_id}",
        json={"name": "Cliente Actualizado", "version": 1},
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["name"] == "Cliente Actualizado"
    assert updated.json()["version"] == 2

    stale = client.patch(
        f"/api/v1/contacts/{contact_id}",
        json={"name": "Versión vieja", "version": 1},
    )
    assert stale.status_code == 409
    assert "versión" in stale.json()["detail"].lower()

    empty_update = client.patch(
        f"/api/v1/contacts/{contact_id}",
        json={"version": 2},
    )
    assert empty_update.status_code == 422

    null_name = client.patch(
        f"/api/v1/contacts/{contact_id}",
        json={"name": None, "version": 2},
    )
    assert null_name.status_code == 422

    cleared_email = client.patch(
        f"/api/v1/contacts/{contact_id}",
        json={"email": None, "version": 2},
    )
    assert cleared_email.status_code == 200
    assert cleared_email.json()["email"] is None


def test_soft_delete_excludes_contact(client: TestClient) -> None:
    first = _create_contact(client, name="Cliente A")
    second = _create_contact(client, name="Cliente B")
    first_id = str(first["id"])
    second_id = str(second["id"])

    deleted = client.delete(f"/api/v1/contacts/{first_id}")
    assert deleted.status_code == 204

    assert client.get(f"/api/v1/contacts/{first_id}").status_code == 404
    assert client.delete(f"/api/v1/contacts/{first_id}").status_code == 404

    listed = client.get("/api/v1/contacts").json()
    listed_ids = {str(contact["id"]) for contact in listed}
    assert second_id in listed_ids
    assert first_id not in listed_ids
