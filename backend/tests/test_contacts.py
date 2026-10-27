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


def test_dian_fields_create_and_update(client: TestClient) -> None:
    """Flujo del formulario de contactos con datos fiscales DIAN (Fase 38A).

    El generador XML rechaza con 422 a los contactos sin estos campos:
    el frontend los envía al crear y al editar (PATCH con versión).
    """
    created = _create_contact(
        client,
        address="Calle 100 # 8-50",
        dv="5",
        person_type="JURIDICA",
        tax_regime="RESPONSABLE_IVA",
        fiscal_responsibility="O-13",
        dian_municipality_code="05001",
        dian_department_code="05",
    )

    assert created["dv"] == "5"
    assert created["person_type"] == "JURIDICA"
    assert created["tax_regime"] == "RESPONSABLE_IVA"
    assert created["fiscal_responsibility"] == "O-13"
    assert created["dian_municipality_code"] == "05001"
    assert created["dian_department_code"] == "05"
    assert created["address"] == "Calle 100 # 8-50"
    assert created["country_code"] == "CO"

    # Edición del resto de datos DIAN sobre el mismo contacto.
    updated = client.patch(
        f"/api/v1/contacts/{created['id']}",
        json={
            "name": "Cliente Uno S.A.S.",
            "address": "Cra 15 # 88 - 21",
            "dv": "8",
            "dian_municipality_code": "11001",
            "dian_department_code": "11",
            "fiscal_responsibility": "R-99-PN",
            "version": created["version"],
        },
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["dv"] == "8"
    assert updated.json()["version"] == created["version"] + 1

    fetched = client.get(f"/api/v1/contacts/{created['id']}").json()
    assert fetched["address"] == "Cra 15 # 88 - 21"
    assert fetched["dian_municipality_code"] == "11001"
    assert fetched["dian_department_code"] == "11"
    assert fetched["fiscal_responsibility"] == "R-99-PN"
    assert fetched["tax_regime"] == "RESPONSABLE_IVA"

    # DV inválido rechazado por el backend (max 2 dígitos definidos en el schema).
    invalid = client.patch(
        f"/api/v1/contacts/{created['id']}",
        json={"dv": "123", "version": fetched["version"]},
    )
    assert invalid.status_code == 422
