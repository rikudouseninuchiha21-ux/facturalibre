"""Tests de creación, emisión y consulta de facturas."""

from __future__ import annotations

from copy import deepcopy
from datetime import date
from decimal import Decimal
from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from httpx import Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.domain.calculations import (
    calculate_invoice_totals,
    calculate_line,
)
from app.domain.models.idempotency_key import IdempotencyKey
from app.domain.models.invoice import Invoice
from app.domain.models.number_sequence import NumberSequence

TWOPLACES = Decimal("0.01")


def _money(value: object) -> Decimal:
    return Decimal(str(value)).quantize(TWOPLACES)


def _create_contact(client: TestClient) -> dict[str, object]:
    response = client.post(
        "/api/v1/contacts",
        json={"name": "Cliente Factura", "email": "factura@example.com"},
    )
    assert response.status_code == 201, response.text
    return response.json()


def _create_tax(client: TestClient) -> dict[str, object]:
    response = client.post(
        "/api/v1/taxes",
        json={"name": "IVA 19 %", "rate": "19.0000"},
    )
    assert response.status_code == 201, response.text
    return response.json()


def _create_item(client: TestClient, tax_id: str) -> dict[str, object]:
    response = client.post(
        "/api/v1/items",
        json={
            "name": "Producto base",
            "description": "Producto base",
            "unit_price": "10.10",
            "tax_id": tax_id,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def _setup_invoice_data(client: TestClient) -> tuple[str, str]:
    contact = _create_contact(client)
    tax = _create_tax(client)
    item = _create_item(client, tax_id=str(tax["id"]))
    return str(contact["id"]), str(item["id"])


def _three_line_payload(contact_id: str, item_id: str) -> dict[str, object]:
    return {
        "contact_id": contact_id,
        "issue_date": "2026-10-21",
        "due_date": "2026-11-20",
        "currency": "COP",
        "lines": [
            {
                "item_id": item_id,
                "quantity": "3",
                "unit_price": "10.10",
                "discount_percent": "10",
            },
            {
                "item_id": item_id,
                "description": "Línea dos",
                "quantity": "2.5",
                "unit_price": "19.99",
                "tax_rate": "19",
            },
            {
                "item_id": item_id,
                "description": "Línea tres",
                "quantity": "1.25",
                "unit_price": "100.00",
                "discount_percent": "5",
                "tax_rate": "19",
            },
        ],
    }


def _post_invoice(
    client: TestClient,
    payload: dict[str, object],
    key: str | None = None,
) -> Response:
    return client.post(
        "/api/v1/invoices",
        json=payload,
        headers={"Idempotency-Key": key or str(uuid4())},
    )


def _issued_invoice(client: TestClient) -> dict[str, object]:
    contact_id, item_id = _setup_invoice_data(client)
    created = _post_invoice(client, _three_line_payload(contact_id, item_id))
    assert created.status_code == 201, created.text

    issued = client.post(f"/api/v1/invoices/{created.json()['id']}/issue")
    assert issued.status_code == 200, issued.text
    return issued.json()


def _void(
    client: TestClient,
    invoice_id: object,
    reason: str = "Error en monto",
) -> Response:
    return client.post(
        f"/api/v1/invoices/{invoice_id}/void",
        json={"reason": reason},
    )


def test_create_invoice_with_three_lines_and_snapshot(
    client: TestClient,
) -> None:
    contact_id, item_id = _setup_invoice_data(client)
    payload = _three_line_payload(contact_id, item_id)

    response = _post_invoice(client, payload)
    assert response.status_code == 201, response.text
    data = response.json()

    assert data["number"] is None
    assert data["lifecycle_status"] == "draft"
    assert data["payment_status"] == "unpaid"
    assert _money(data["subtotal"]) == Decimal("196.00")
    assert _money(data["tax_total"]) == Decimal("37.24")
    assert _money(data["total"]) == Decimal("233.24")
    assert _money(data["balance"]) == Decimal("233.24")

    by_description = {line["description"]: line for line in data["lines"]}
    first = by_description["Producto base"]
    second = by_description["Línea dos"]
    third = by_description["Línea tres"]

    assert _money(first["line_subtotal"]) == Decimal("27.27")
    assert _money(first["line_tax"]) == Decimal("5.18")
    assert _money(first["line_total"]) == Decimal("32.45")
    assert _money(second["line_subtotal"]) == Decimal("49.98")
    assert _money(second["line_tax"]) == Decimal("9.50")
    assert _money(second["line_total"]) == Decimal("59.48")
    assert _money(third["line_subtotal"]) == Decimal("118.75")
    assert _money(third["line_tax"]) == Decimal("22.56")
    assert _money(third["line_total"]) == Decimal("141.31")

    invoice_id = data["id"]
    fetched = client.get(f"/api/v1/invoices/{invoice_id}")
    assert fetched.status_code == 200
    assert fetched.json()["total"] == data["total"]

    listed = client.get("/api/v1/invoices?limit=1&offset=0")
    assert listed.status_code == 200
    assert len(listed.json()) == 1

    # El ítem cambia después de crear la factura; la línea conserva el snapshot.
    item_update = client.patch(
        f"/api/v1/items/{item_id}",
        json={
            "description": "Descripción nueva",
            "unit_price": "999.99",
            "version": 1,
        },
    )
    assert item_update.status_code == 200, item_update.text

    after_item_change = client.get(f"/api/v1/invoices/{invoice_id}").json()
    snapshot = {line["description"]: line for line in after_item_change["lines"]}
    assert snapshot["Producto base"]["unit_price"] == "10.10"
    assert snapshot["Producto base"]["description"] == "Producto base"


def test_create_invoice_is_idempotent_with_same_key_and_body(
    client: TestClient,
    db_session: Session,
) -> None:
    contact_id, item_id = _setup_invoice_data(client)
    payload = _three_line_payload(contact_id, item_id)
    key = str(uuid4())

    first = _post_invoice(client, payload, key)
    second = _post_invoice(client, payload, key)

    assert first.status_code == 201, first.text
    assert second.status_code == 201, second.text
    assert first.json() == second.json()

    invoice_count = db_session.scalar(select(func.count()).select_from(Invoice))
    key_count = db_session.scalar(select(func.count()).select_from(IdempotencyKey))
    assert invoice_count == 1
    assert key_count == 1


def test_create_invoice_rejects_same_key_with_different_body(
    client: TestClient,
    db_session: Session,
) -> None:
    contact_id, item_id = _setup_invoice_data(client)
    payload = _three_line_payload(contact_id, item_id)
    key = str(uuid4())

    first = _post_invoice(client, payload, key)
    assert first.status_code == 201, first.text

    changed = deepcopy(payload)
    changed["lines"][0]["quantity"] = "4"
    second = _post_invoice(client, changed, key)

    assert second.status_code == 409
    assert second.json() == {"detail": "Idempotency-Key reutilizada con body diferente"}
    invoice_count = db_session.scalar(select(func.count()).select_from(Invoice))
    assert invoice_count == 1


def test_issue_assigns_sequential_numbers(
    client: TestClient,
    db_session: Session,
) -> None:
    contact_id, item_id = _setup_invoice_data(client)
    payload = _three_line_payload(contact_id, item_id)

    first = _post_invoice(client, payload)
    second = _post_invoice(client, payload)
    assert first.status_code == 201, first.text
    assert second.status_code == 201, second.text

    first_issue = client.post(f"/api/v1/invoices/{first.json()['id']}/issue")
    second_issue = client.post(f"/api/v1/invoices/{second.json()['id']}/issue")

    assert first_issue.status_code == 200, first_issue.text
    assert second_issue.status_code == 200, second_issue.text
    assert first_issue.json()["number"] == "FV00000001"
    assert second_issue.json()["number"] == "FV00000002"
    assert first_issue.json()["lifecycle_status"] == "issued"
    assert first_issue.json()["payment_status"] == "unpaid"
    assert first_issue.json()["version"] == 2

    sequence = db_session.scalar(select(NumberSequence).where(NumberSequence.name == "invoice"))
    assert sequence is not None
    assert sequence.next_number == 3


def test_issue_issued_invoice_returns_409(client: TestClient) -> None:
    contact_id, item_id = _setup_invoice_data(client)
    created = _post_invoice(client, _three_line_payload(contact_id, item_id))
    invoice_id = created.json()["id"]

    issued = client.post(f"/api/v1/invoices/{invoice_id}/issue")
    assert issued.status_code == 200, issued.text

    repeated = client.post(f"/api/v1/invoices/{invoice_id}/issue")
    assert repeated.status_code == 409
    assert repeated.json() == {"detail": "Solo se emiten facturas en estado borrador"}


def test_delete_only_allows_drafts(client: TestClient) -> None:
    contact_id, item_id = _setup_invoice_data(client)
    payload = _three_line_payload(contact_id, item_id)

    draft = _post_invoice(client, payload)
    draft_id = draft.json()["id"]
    deleted = client.delete(f"/api/v1/invoices/{draft_id}")
    assert deleted.status_code == 204
    assert client.get(f"/api/v1/invoices/{draft_id}").status_code == 404

    issued = _post_invoice(client, payload)
    issued_id = issued.json()["id"]
    assert client.post(f"/api/v1/invoices/{issued_id}/issue").status_code == 200

    forbidden = client.delete(f"/api/v1/invoices/{issued_id}")
    assert forbidden.status_code == 409
    assert forbidden.json() == {"detail": "Solo se eliminan borradores"}

    listed_ids = {invoice["id"] for invoice in client.get("/api/v1/invoices").json()}
    assert draft_id not in listed_ids
    assert issued_id in listed_ids


def test_delete_draft_soft_deletes(client: TestClient, db_session: Session) -> None:
    contact_id, item_id = _setup_invoice_data(client)
    draft = _post_invoice(client, _three_line_payload(contact_id, item_id))
    invoice_id = str(draft.json()["id"])

    deleted = client.delete(f"/api/v1/invoices/{invoice_id}")

    assert deleted.status_code == 204
    assert client.get(f"/api/v1/invoices/{invoice_id}").status_code == 404
    listed_ids = {invoice["id"] for invoice in client.get("/api/v1/invoices").json()}
    assert invoice_id not in listed_ids

    row = db_session.execute(
        select(Invoice.id, Invoice.version, Invoice.deleted_at).where(
            Invoice.id == UUID(invoice_id)
        )
    ).one_or_none()
    assert row is not None
    assert row.deleted_at is not None
    assert row.version == 2


def test_delete_issued_returns_409(client: TestClient) -> None:
    invoice = _issued_invoice(client)

    response = client.delete(f"/api/v1/invoices/{invoice['id']}")

    assert response.status_code == 409
    assert response.json() == {"detail": "Solo se eliminan borradores"}
    assert client.get(f"/api/v1/invoices/{invoice['id']}").status_code == 200


def test_issue_deleted_draft_returns_404(client: TestClient) -> None:
    contact_id, item_id = _setup_invoice_data(client)
    draft = _post_invoice(client, _three_line_payload(contact_id, item_id))
    invoice_id = draft.json()["id"]
    assert client.delete(f"/api/v1/invoices/{invoice_id}").status_code == 204

    response = client.post(f"/api/v1/invoices/{invoice_id}/issue")

    assert response.status_code == 404
    assert response.json() == {"detail": "Factura no encontrada"}


def test_pay_deleted_invoice_returns_404(client: TestClient) -> None:
    contact_id, item_id = _setup_invoice_data(client)
    draft = _post_invoice(client, _three_line_payload(contact_id, item_id))
    invoice_id = draft.json()["id"]
    assert client.delete(f"/api/v1/invoices/{invoice_id}").status_code == 204

    response = client.post(
        f"/api/v1/invoices/{invoice_id}/payments",
        headers={"Idempotency-Key": str(uuid4())},
        json={
            "amount": "10.00",
            "payment_date": date.today().isoformat(),
            "method": "cash",
        },
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Factura no encontrada"}


def test_list_excludes_deleted(client: TestClient) -> None:
    contact_id, item_id = _setup_invoice_data(client)
    payload = _three_line_payload(contact_id, item_id)

    kept = _post_invoice(client, payload)
    deleted = _post_invoice(client, payload)
    assert kept.status_code == 201, kept.text
    assert deleted.status_code == 201, deleted.text
    deleted_id = deleted.json()["id"]

    assert client.delete(f"/api/v1/invoices/{deleted_id}").status_code == 204

    listed = client.get("/api/v1/invoices")

    assert listed.status_code == 200
    assert [invoice["id"] for invoice in listed.json()] == [kept.json()["id"]]


def test_due_date_before_issue_date_is_422(client: TestClient) -> None:
    contact_id, item_id = _setup_invoice_data(client)
    payload = _three_line_payload(contact_id, item_id)
    payload["due_date"] = "2026-10-20"

    response = _post_invoice(client, payload)
    assert response.status_code == 422


def test_currency_other_than_cop_is_422(client: TestClient) -> None:
    contact_id, item_id = _setup_invoice_data(client)
    payload = _three_line_payload(contact_id, item_id)
    payload["currency"] = "USD"

    response = _post_invoice(client, payload)
    assert response.status_code == 422


def test_missing_idempotency_key_is_422(client: TestClient) -> None:
    contact_id, item_id = _setup_invoice_data(client)
    payload = _three_line_payload(contact_id, item_id)

    response = client.post("/api/v1/invoices", json=payload)
    assert response.status_code == 422


def test_calculation_rounding_matches_expected_values() -> None:
    lines = [
        calculate_line(
            quantity=Decimal("3"),
            unit_price=Decimal("10.10"),
            discount_percent=Decimal("10"),
            tax_rate=Decimal("19"),
        ),
        calculate_line(
            quantity=Decimal("2.5"),
            unit_price=Decimal("19.99"),
            discount_percent=Decimal("0"),
            tax_rate=Decimal("19"),
        ),
        calculate_line(
            quantity=Decimal("1.25"),
            unit_price=Decimal("100.00"),
            discount_percent=Decimal("5"),
            tax_rate=Decimal("19"),
        ),
    ]
    totals = calculate_invoice_totals(lines)

    assert [line.subtotal for line in lines] == [
        Decimal("27.27"),
        Decimal("49.98"),
        Decimal("118.75"),
    ]
    assert [line.tax for line in lines] == [
        Decimal("5.18"),
        Decimal("9.50"),
        Decimal("22.56"),
    ]
    assert totals.subtotal == Decimal("196.00")
    assert totals.tax_total == Decimal("37.24")
    assert totals.total == Decimal("233.24")
    assert totals.balance == Decimal("233.24")


def test_void_issued_invoice_without_payments(client: TestClient) -> None:
    invoice = _issued_invoice(client)
    issued_version = invoice["version"]

    response = _void(client, invoice["id"], "Error en monto")

    assert response.status_code == 200, response.text
    voided = response.json()
    assert voided["lifecycle_status"] == "void"
    assert voided["voided_reason"] == "Error en monto"
    assert voided["voided_at"] is not None
    assert voided["version"] == issued_version + 1
    assert voided["payment_status"] == "unpaid"


def test_get_invoice_shows_void_fields(client: TestClient) -> None:
    invoice = _issued_invoice(client)
    assert _void(client, invoice["id"], "Cliente canceló").status_code == 200

    fetched = client.get(f"/api/v1/invoices/{invoice['id']}")

    assert fetched.status_code == 200
    data = fetched.json()
    assert data["lifecycle_status"] == "void"
    assert data["voided_reason"] == "Cliente canceló"
    assert data["voided_at"] is not None


def test_void_draft_invoice_returns_409(client: TestClient) -> None:
    contact_id, item_id = _setup_invoice_data(client)
    draft = _post_invoice(client, _three_line_payload(contact_id, item_id))

    response = _void(client, draft.json()["id"])

    assert response.status_code == 409
    assert response.json() == {
        "detail": "No se puede anular un borrador, elimínelo",
    }


def test_void_already_void_invoice_returns_409(client: TestClient) -> None:
    invoice = _issued_invoice(client)
    first = _void(client, invoice["id"])
    assert first.status_code == 200, first.text

    repeated = _void(client, invoice["id"], "Segundo intento")

    assert repeated.status_code == 409
    assert repeated.json() == {"detail": "Factura ya anulada"}


def test_void_invoice_with_payment_returns_409(client: TestClient) -> None:
    invoice = _issued_invoice(client)
    payment = client.post(
        f"/api/v1/invoices/{invoice['id']}/payments",
        headers={"Idempotency-Key": str(uuid4())},
        json={
            "amount": "10.00",
            "payment_date": date.today().isoformat(),
            "method": "cash",
        },
    )
    assert payment.status_code == 201, payment.text

    response = _void(client, invoice["id"])

    assert response.status_code == 409
    assert response.json() == {
        "detail": "Factura con pagos. Use nota crédito (no implementada en MVP)",
    }
    still_issued = client.get(f"/api/v1/invoices/{invoice['id']}").json()
    assert still_issued["lifecycle_status"] == "issued"
    assert still_issued["payment_status"] == "partially_paid"


def test_void_missing_reason_is_422(client: TestClient) -> None:
    invoice = _issued_invoice(client)

    response = client.post(f"/api/v1/invoices/{invoice['id']}/void", json={})

    assert response.status_code == 422


def test_void_empty_reason_is_422(client: TestClient) -> None:
    invoice = _issued_invoice(client)

    for reason in ("", "   "):
        response = client.post(
            f"/api/v1/invoices/{invoice['id']}/void",
            json={"reason": reason},
        )
        assert response.status_code == 422


def test_issue_void_invoice_returns_409(client: TestClient) -> None:
    invoice = _issued_invoice(client)
    assert _void(client, invoice["id"]).status_code == 200

    response = client.post(f"/api/v1/invoices/{invoice['id']}/issue")

    assert response.status_code == 409
    assert response.json() == {
        "detail": "Solo se emiten facturas en estado borrador",
    }


def test_delete_void_invoice_returns_409(client: TestClient) -> None:
    invoice = _issued_invoice(client)
    assert _void(client, invoice["id"]).status_code == 200

    response = client.delete(f"/api/v1/invoices/{invoice['id']}")

    assert response.status_code == 409
    assert response.json() == {"detail": "Solo se eliminan borradores"}


def test_void_missing_invoice_returns_404(client: TestClient) -> None:
    response = _void(client, uuid4())

    assert response.status_code == 404
    assert response.json() == {"detail": "Factura no encontrada"}
