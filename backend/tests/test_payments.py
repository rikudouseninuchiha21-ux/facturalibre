"""Tests de pagos sobre facturas emitidas.

REQUIERE VALIDACIÓN: la prueba de concurrencia real con dos requests HTTP
simultáneos necesita dos sesiones de base de datos independientes y datos
commiteados. El código usa SELECT ... FOR UPDATE sobre la factura; esa prueba
de concurrencia queda pendiente de validación fuera de la sesión transaccional
compartida de esta suite.
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from uuid import uuid4

from fastapi.testclient import TestClient
from httpx import Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.domain.models.payment import Payment

TWOPLACES = Decimal("0.01")


def _money(value: object) -> Decimal:
    return Decimal(str(value)).quantize(TWOPLACES)


def _create_invoice(client: TestClient, total: str = "100.00") -> dict[str, object]:
    """Crea una factura DRAFT con una línea sin impuesto."""
    today = date.today()
    contact = client.post(
        "/api/v1/contacts",
        json={"name": "Cliente Pagos", "email": "pagos@example.com"},
    )
    assert contact.status_code == 201, contact.text

    item = client.post(
        "/api/v1/items",
        json={
            "name": "Producto para pagos",
            "description": "Producto para pagos",
            "unit_price": total,
            "tax_id": None,
        },
    )
    assert item.status_code == 201, item.text

    response = client.post(
        "/api/v1/invoices",
        json={
            "contact_id": contact.json()["id"],
            "issue_date": today.isoformat(),
            "due_date": (today + timedelta(days=30)).isoformat(),
            "currency": "COP",
            "lines": [
                {
                    "item_id": item.json()["id"],
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


def _issued_invoice(client: TestClient, total: str = "100.00") -> dict[str, object]:
    invoice = _create_invoice(client, total)
    response = client.post(f"/api/v1/invoices/{invoice['id']}/issue")
    assert response.status_code == 200, response.text
    return response.json()


def _pay(
    client: TestClient,
    invoice_id: object,
    amount: str,
    *,
    key: str | None = None,
    payment_date: str | None = None,
    method: str = "cash",
    reference: str | None = None,
) -> Response:
    body: dict[str, object] = {
        "amount": amount,
        "payment_date": payment_date or date.today().isoformat(),
        "method": method,
    }
    if reference is not None:
        body["reference"] = reference
    return client.post(
        f"/api/v1/invoices/{invoice_id}/payments",
        json=body,
        headers={"Idempotency-Key": key or str(uuid4())},
    )


def _get_invoice(client: TestClient, invoice_id: object) -> dict[str, object]:
    response = client.get(f"/api/v1/invoices/{invoice_id}")
    assert response.status_code == 200, response.text
    return response.json()


def test_partial_payment_updates_balance_status_and_version(
    client: TestClient,
) -> None:
    invoice = _issued_invoice(client, "100.00")
    invoice_id = invoice["id"]
    initial_version = invoice["version"]

    response = _pay(client, invoice_id, "30.00", reference="TRX-001")

    assert response.status_code == 201, response.text
    payment = response.json()
    assert payment["invoice_id"] == invoice_id
    assert _money(payment["amount"]) == Decimal("30.00")
    assert payment["method"] == "cash"
    assert payment["reference"] == "TRX-001"

    updated = _get_invoice(client, invoice_id)
    assert _money(updated["balance"]) == Decimal("70.00")
    assert updated["payment_status"] == "partially_paid"
    assert updated["version"] == initial_version + 1

    listed = client.get(f"/api/v1/invoices/{invoice_id}/payments")
    assert listed.status_code == 200, listed.text
    assert [item["id"] for item in listed.json()] == [payment["id"]]


def test_exact_payment_marks_invoice_as_paid(client: TestClient) -> None:
    invoice = _issued_invoice(client, "100.00")

    response = _pay(client, invoice["id"], "100.00")

    assert response.status_code == 201, response.text
    updated = _get_invoice(client, invoice["id"])
    assert _money(updated["balance"]) == Decimal("0.00")
    assert updated["payment_status"] == "paid"


def test_overpayment_is_rejected_without_changing_invoice(
    client: TestClient,
    db_session: Session,
) -> None:
    invoice = _issued_invoice(client, "100.00")

    response = _pay(client, invoice["id"], "150.00")

    assert response.status_code == 422
    assert response.json() == {"detail": "Sobrepago no permitido en MVP"}

    updated = _get_invoice(client, invoice["id"])
    assert _money(updated["balance"]) == Decimal("100.00")
    assert updated["payment_status"] == "unpaid"
    assert updated["version"] == invoice["version"]
    assert db_session.scalar(select(func.count()).select_from(Payment)) == 0


def test_payment_on_draft_invoice_returns_409(client: TestClient) -> None:
    invoice = _create_invoice(client, "100.00")

    response = _pay(client, invoice["id"], "10.00")

    assert response.status_code == 409
    assert response.json() == {"detail": "Solo se puede pagar una factura emitida"}

    unchanged = _get_invoice(client, invoice["id"])
    assert _money(unchanged["balance"]) == Decimal("100.00")
    assert unchanged["payment_status"] == "unpaid"


def test_payment_on_paid_invoice_is_overpayment(client: TestClient) -> None:
    invoice = _issued_invoice(client, "100.00")
    first = _pay(client, invoice["id"], "100.00")
    assert first.status_code == 201, first.text

    response = _pay(client, invoice["id"], "1.00")

    assert response.status_code == 422
    assert response.json() == {"detail": "Sobrepago no permitido en MVP"}
    updated = _get_invoice(client, invoice["id"])
    assert _money(updated["balance"]) == Decimal("0.00")
    assert updated["payment_status"] == "paid"


def test_payment_idempotency_replays_and_rejects_different_body(
    client: TestClient,
    db_session: Session,
) -> None:
    invoice = _issued_invoice(client, "100.00")
    key = str(uuid4())

    first = _pay(client, invoice["id"], "30.00", key=key)
    repeated = _pay(client, invoice["id"], "30.00", key=key)

    assert first.status_code == 201, first.text
    assert repeated.status_code == 201, repeated.text
    assert repeated.json() == first.json()
    assert db_session.scalar(select(func.count()).select_from(Payment)) == 1

    changed = _pay(client, invoice["id"], "20.00", key=key)
    assert changed.status_code == 409
    assert changed.json() == {"detail": "Idempotency-Key reutilizada con body diferente"}
    assert db_session.scalar(select(func.count()).select_from(Payment)) == 1

    updated = _get_invoice(client, invoice["id"])
    assert _money(updated["balance"]) == Decimal("70.00")
    assert updated["payment_status"] == "partially_paid"


def test_delete_payment_recalculates_invoice(client: TestClient) -> None:
    invoice = _issued_invoice(client, "100.00")
    invoice_id = invoice["id"]
    initial_version = invoice["version"]

    first = _pay(client, invoice_id, "30.00")
    second = _pay(client, invoice_id, "70.00")
    assert first.status_code == 201, first.text
    assert second.status_code == 201, second.text

    paid = _get_invoice(client, invoice_id)
    assert _money(paid["balance"]) == Decimal("0.00")
    assert paid["payment_status"] == "paid"

    deleted_second = client.delete(f"/api/v1/invoices/{invoice_id}/payments/{second.json()['id']}")
    assert deleted_second.status_code == 204

    after_second_delete = _get_invoice(client, invoice_id)
    assert _money(after_second_delete["balance"]) == Decimal("70.00")
    assert after_second_delete["payment_status"] == "partially_paid"
    assert after_second_delete["version"] == initial_version + 3

    remaining = client.get(f"/api/v1/invoices/{invoice_id}/payments")
    assert remaining.status_code == 200
    assert [item["id"] for item in remaining.json()] == [first.json()["id"]]

    deleted_first = client.delete(f"/api/v1/invoices/{invoice_id}/payments/{first.json()['id']}")
    assert deleted_first.status_code == 204

    after_all_deletes = _get_invoice(client, invoice_id)
    assert _money(after_all_deletes["balance"]) == Decimal("100.00")
    assert after_all_deletes["payment_status"] == "unpaid"
    assert after_all_deletes["version"] == initial_version + 4

    repeated = client.delete(f"/api/v1/invoices/{invoice_id}/payments/{first.json()['id']}")
    assert repeated.status_code == 404
    assert repeated.json() == {"detail": "Pago no encontrado"}


def test_list_payments_orders_by_date_desc_and_paginates(client: TestClient) -> None:
    invoice = _issued_invoice(client, "100.00")
    today = date.today()
    yesterday = today - timedelta(days=1)

    old = _pay(
        client,
        invoice["id"],
        "10.00",
        payment_date=yesterday.isoformat(),
    )
    recent = _pay(
        client,
        invoice["id"],
        "20.00",
        payment_date=today.isoformat(),
    )
    assert old.status_code == 201, old.text
    assert recent.status_code == 201, recent.text

    first_page = client.get(f"/api/v1/invoices/{invoice['id']}/payments?limit=1&offset=0")
    second_page = client.get(f"/api/v1/invoices/{invoice['id']}/payments?limit=1&offset=1")

    assert first_page.status_code == 200
    assert second_page.status_code == 200
    assert first_page.json()[0]["id"] == recent.json()["id"]
    assert second_page.json()[0]["id"] == old.json()["id"]
    assert first_page.json()[0]["payment_date"] > second_page.json()[0]["payment_date"]


def test_payment_date_in_future_is_422(
    client: TestClient,
    db_session: Session,
) -> None:
    invoice = _issued_invoice(client, "100.00")

    response = _pay(
        client,
        invoice["id"],
        "10.00",
        payment_date=(date.today() + timedelta(days=1)).isoformat(),
    )

    assert response.status_code == 422
    assert db_session.scalar(select(func.count()).select_from(Payment)) == 0


def test_missing_idempotency_key_is_422(client: TestClient) -> None:
    invoice = _issued_invoice(client, "100.00")

    response = client.post(
        f"/api/v1/invoices/{invoice['id']}/payments",
        json={
            "amount": "10.00",
            "payment_date": date.today().isoformat(),
            "method": "cash",
        },
    )

    assert response.status_code == 422


def test_payment_on_missing_invoice_returns_404(client: TestClient) -> None:
    response = _pay(client, uuid4(), "10.00")

    assert response.status_code == 404
    assert response.json() == {"detail": "Factura no encontrada"}


def test_delete_missing_payment_returns_404(client: TestClient) -> None:
    invoice = _issued_invoice(client, "100.00")

    response = client.delete(f"/api/v1/invoices/{invoice['id']}/payments/{uuid4()}")

    assert response.status_code == 404
    assert response.json() == {"detail": "Pago no encontrado"}
    unchanged = _get_invoice(client, invoice["id"])
    assert unchanged["version"] == invoice["version"]
