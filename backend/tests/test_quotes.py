"""Tests de cotizaciones: CRUD, cambios de estado y conversión a factura."""

from __future__ import annotations

from decimal import Decimal
from typing import Any
from uuid import uuid4

from fastapi.testclient import TestClient

TWOPLACES = Decimal("0.01")


def _money(value: object) -> Decimal:
    return Decimal(str(value)).quantize(TWOPLACES)


def _create_contact(client: TestClient) -> dict[str, Any]:
    response = client.post(
        "/api/v1/contacts",
        json={"name": "Cliente Cotización", "email": "cotizacion@example.com"},
    )
    assert response.status_code == 201, response.text
    return response.json()


def _create_tax(client: TestClient) -> dict[str, Any]:
    response = client.post(
        "/api/v1/taxes",
        json={"name": "IVA 19 %", "rate": "19.0000"},
    )
    assert response.status_code == 201, response.text
    return response.json()


def _create_item(client: TestClient, tax_id: str) -> dict[str, Any]:
    response = client.post(
        "/api/v1/items",
        json={
            "name": "Producto Cotización",
            "description": "Producto para cotizar",
            "unit_price": "100.00",
            "tax_id": tax_id,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def _create_warehouse(client: TestClient) -> dict[str, Any]:
    """Crea la bodega principal activa requerida para descontar inventario."""
    response = client.post(
        "/api/v1/warehouses",
        json={"name": "Bodega Principal", "code": "PRINCIPAL"},
    )
    assert response.status_code == 201, response.text
    return response.json()


def _stock_item(client: TestClient, item_id: str, warehouse_id: str, quantity: str = "100") -> None:
    """Carga stock inicial para que la conversión pueda descontar inventario."""
    response = client.post(
        "/api/v1/inventory/movements",
        json={
            "item_id": item_id,
            "warehouse_id": warehouse_id,
            "movement_type": "IN",
            "quantity": quantity,
        },
    )
    assert response.status_code == 201, response.text


def _setup_quote_data(client: TestClient) -> tuple[str, str]:
    contact = _create_contact(client)
    tax = _create_tax(client)
    item = _create_item(client, tax_id=str(tax["id"]))
    warehouse = _create_warehouse(client)
    _stock_item(client, str(item["id"]), str(warehouse["id"]))
    return str(contact["id"]), str(item["id"])


def _quote_payload(contact_id: str, item_id: str) -> dict[str, Any]:
    return {
        "contact_id": contact_id,
        "issue_date": "2026-10-24",
        "expiry_date": "2026-11-24",
        "currency": "COP",
        "lines": [
            {
                "item_id": item_id,
                "quantity": "2",
                "unit_price": "100.00",
                "tax_rate": "19",
            },
        ],
    }


def _post_quote(
    client: TestClient,
    payload: dict[str, Any],
    key: str | None = None,
) -> Any:
    return client.post(
        "/api/v1/quotes",
        json=payload,
        headers={"Idempotency-Key": key or str(uuid4())},
    )


def _patch_quote_status(
    client: TestClient,
    quote_id: str,
    status: str,
) -> Any:
    return client.patch(
        f"/api/v1/quotes/{quote_id}/status",
        json={"status": status},
    )


def test_create_quote_draft(client: TestClient) -> None:
    contact_id, item_id = _setup_quote_data(client)
    response = _post_quote(client, _quote_payload(contact_id, item_id))
    assert response.status_code == 201, response.text
    data = response.json()

    assert data["number"] is None
    assert data["status"] == "DRAFT"
    assert data["converted_invoice_id"] is None
    assert _money(data["subtotal"]) == Decimal("200.00")
    assert _money(data["tax_total"]) == Decimal("38.00")
    assert _money(data["total"]) == Decimal("238.00")
    assert len(data["lines"]) == 1


def test_get_quote_by_id(client: TestClient) -> None:
    contact_id, item_id = _setup_quote_data(client)
    created = _post_quote(client, _quote_payload(contact_id, item_id))
    assert created.status_code == 201, created.text
    quote_id = created.json()["id"]

    fetched = client.get(f"/api/v1/quotes/{quote_id}")
    assert fetched.status_code == 200
    assert fetched.json()["id"] == quote_id
    assert fetched.json()["status"] == "DRAFT"


def test_list_quotes(client: TestClient) -> None:
    contact_id, item_id = _setup_quote_data(client)
    _post_quote(client, _quote_payload(contact_id, item_id))

    listed = client.get("/api/v1/quotes")
    assert listed.status_code == 200
    assert len(listed.json()) == 1


def test_delete_only_allows_drafts(client: TestClient) -> None:
    contact_id, item_id = _setup_quote_data(client)
    draft = _post_quote(client, _quote_payload(contact_id, item_id))
    draft_id = draft.json()["id"]

    deleted = client.delete(f"/api/v1/quotes/{draft_id}")
    assert deleted.status_code == 204, deleted.text
    assert client.get(f"/api/v1/quotes/{draft_id}").status_code == 404


def test_delete_non_draft_returns_409(client: TestClient) -> None:
    contact_id, item_id = _setup_quote_data(client)
    draft = _post_quote(client, _quote_payload(contact_id, item_id))
    quote_id = draft.json()["id"]

    # Pasar a SENT
    assert _patch_quote_status(client, quote_id, "SENT").status_code == 200

    forbidden = client.delete(f"/api/v1/quotes/{quote_id}")
    assert forbidden.status_code == 409
    assert forbidden.json() == {"detail": "Solo se eliminan cotizaciones en borrador"}


def test_transition_draft_to_sent(client: TestClient) -> None:
    contact_id, item_id = _setup_quote_data(client)
    draft = _post_quote(client, _quote_payload(contact_id, item_id))
    quote_id = draft.json()["id"]

    response = _patch_quote_status(client, quote_id, "SENT")
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "SENT"


def test_transition_sent_to_accepted(client: TestClient) -> None:
    contact_id, item_id = _setup_quote_data(client)
    draft = _post_quote(client, _quote_payload(contact_id, item_id))
    quote_id = draft.json()["id"]

    assert _patch_quote_status(client, quote_id, "SENT").status_code == 200
    response = _patch_quote_status(client, quote_id, "ACCEPTED")
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "ACCEPTED"


def test_transition_sent_to_rejected(client: TestClient) -> None:
    contact_id, item_id = _setup_quote_data(client)
    draft = _post_quote(client, _quote_payload(contact_id, item_id))
    quote_id = draft.json()["id"]

    assert _patch_quote_status(client, quote_id, "SENT").status_code == 200
    response = _patch_quote_status(client, quote_id, "REJECTED")
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "REJECTED"


def test_invalid_transition_draft_to_accepted_returns_409(client: TestClient) -> None:
    contact_id, item_id = _setup_quote_data(client)
    draft = _post_quote(client, _quote_payload(contact_id, item_id))
    quote_id = draft.json()["id"]

    response = _patch_quote_status(client, quote_id, "ACCEPTED")
    assert response.status_code == 409
    assert "No se puede pasar de DRAFT a ACCEPTED" in response.json()["detail"]


def test_invalid_transition_draft_to_rejected_returns_409(client: TestClient) -> None:
    contact_id, item_id = _setup_quote_data(client)
    draft = _post_quote(client, _quote_payload(contact_id, item_id))
    quote_id = draft.json()["id"]

    response = _patch_quote_status(client, quote_id, "REJECTED")
    assert response.status_code == 409
    assert "No se puede pasar de DRAFT a REJECTED" in response.json()["detail"]


def test_convert_accepted_quote_to_invoice(client: TestClient) -> None:
    """Una cotización ACCEPTED se convierte en factura emitida, descuenta stock
    y cambia el contacto a CUSTOMER. Requiere bodega activa PRINCIPAL."""
    contact_id, item_id = _setup_quote_data(client)
    draft = _post_quote(client, _quote_payload(contact_id, item_id))
    quote_id = draft.json()["id"]

    assert _patch_quote_status(client, quote_id, "SENT").status_code == 200
    assert _patch_quote_status(client, quote_id, "ACCEPTED").status_code == 200

    converted = client.post(
        f"/api/v1/quotes/{quote_id}/convert-to-invoice",
    )
    assert converted.status_code == 200, converted.text
    data = converted.json()

    assert data["status"] == "CONVERTED"
    assert data["converted_invoice_id"] is not None

    # La factura vinculada debe existir y estar emitida
    invoice_id = data["converted_invoice_id"]
    invoice = client.get(f"/api/v1/invoices/{invoice_id}")
    assert invoice.status_code == 200
    assert invoice.json()["lifecycle_status"] == "issued"

    # El contacto debe haber pasado a CUSTOMER
    contact = client.get(f"/api/v1/contacts/{contact_id}")
    assert contact.status_code == 200
    assert contact.json()["type"] == "customer"


def test_convert_non_accepted_quote_returns_409(client: TestClient) -> None:
    contact_id, item_id = _setup_quote_data(client)
    draft = _post_quote(client, _quote_payload(contact_id, item_id))
    quote_id = draft.json()["id"]

    response = client.post(f"/api/v1/quotes/{quote_id}/convert-to-invoice")
    assert response.status_code == 409
    assert "Solo se pueden convertir cotizaciones en estado ACEPTADA" in response.json()["detail"]


def test_convert_already_converted_quote_returns_409(client: TestClient) -> None:
    contact_id, item_id = _setup_quote_data(client)
    draft = _post_quote(client, _quote_payload(contact_id, item_id))
    quote_id = draft.json()["id"]

    assert _patch_quote_status(client, quote_id, "SENT").status_code == 200
    assert _patch_quote_status(client, quote_id, "ACCEPTED").status_code == 200

    first = client.post(f"/api/v1/quotes/{quote_id}/convert-to-invoice")
    assert first.status_code == 200, first.text

    second = client.post(f"/api/v1/quotes/{quote_id}/convert-to-invoice")
    assert second.status_code == 409
    assert "ya fue convertida a factura" in second.json()["detail"]
