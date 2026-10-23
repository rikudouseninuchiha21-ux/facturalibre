"""Tests del catálogo PUC y de la generación automática de asientos."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.application.accounting.service import AccountingError
from app.domain.models.accounting import (
    AccountingAccount,
    AccountingEntry,
    AccountingEntryLine,
)
from app.domain.models.payment import Payment

TWOPLACES = Decimal("0.01")
ZERO = Decimal("0.00")


def _money(value: object) -> Decimal:
    return Decimal(str(value)).quantize(TWOPLACES)


def _create_contact(client: TestClient) -> dict[str, object]:
    response = client.post(
        "/api/v1/contacts",
        json={"name": "Cliente Contabilidad", "email": "contabilidad@example.com"},
    )
    assert response.status_code == 201, response.text
    return response.json()


def _create_tax(client: TestClient, rate: str = "19.0000") -> dict[str, object]:
    response = client.post(
        "/api/v1/taxes",
        json={"name": f"IVA {rate} %", "rate": rate},
    )
    assert response.status_code == 201, response.text
    return response.json()


def _create_item(
    client: TestClient,
    *,
    unit_price: str,
    tax_id: str | None,
) -> dict[str, object]:
    response = client.post(
        "/api/v1/items",
        json={
            "name": "Producto contable",
            "description": "Producto contable",
            "unit_price": unit_price,
            "tax_id": tax_id,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def _stock_item(client: TestClient, item_id: str, quantity: str = "100") -> None:
    """Crea la bodega principal y carga stock inicial para los tests de emisión."""
    warehouse = client.post(
        "/api/v1/warehouses",
        json={"name": "Bodega principal", "code": "PRINCIPAL"},
    )
    assert warehouse.status_code == 201, warehouse.text
    movement = client.post(
        "/api/v1/inventory/movements",
        json={
            "item_id": item_id,
            "warehouse_id": warehouse.json()["id"],
            "movement_type": "IN",
            "quantity": quantity,
        },
    )
    assert movement.status_code == 201, movement.text


def _create_invoice(
    client: TestClient,
    *,
    unit_price: str = "100.00",
    tax_rate: str = "19",
) -> dict[str, object]:
    contact = _create_contact(client)
    tax_id: str | None = None
    if tax_rate != "0":
        tax = _create_tax(client, f"{Decimal(tax_rate):.4f}")
        tax_id = str(tax["id"])

    item = _create_item(client, unit_price=unit_price, tax_id=tax_id)
    _stock_item(client, str(item["id"]))
    today = date.today()
    response = client.post(
        "/api/v1/invoices",
        headers={"Idempotency-Key": str(uuid4())},
        json={
            "contact_id": contact["id"],
            "issue_date": today.isoformat(),
            "due_date": (today + timedelta(days=30)).isoformat(),
            "currency": "COP",
            "lines": [
                {
                    "item_id": item["id"],
                    "quantity": "1",
                    "unit_price": unit_price,
                    "discount_percent": "0",
                    "tax_rate": tax_rate,
                }
            ],
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def _issue_invoice(
    client: TestClient,
    *,
    unit_price: str = "100.00",
    tax_rate: str = "19",
) -> dict[str, object]:
    invoice = _create_invoice(client, unit_price=unit_price, tax_rate=tax_rate)
    response = client.post(f"/api/v1/invoices/{invoice['id']}/issue")
    assert response.status_code == 200, response.text
    return response.json()


def _entries(client: TestClient) -> list[dict[str, object]]:
    response = client.get("/api/v1/accounting/entries?limit=100")
    assert response.status_code == 200, response.text
    return response.json()


def _entry_for(
    client: TestClient,
    source_type: str,
    source_id: object,
) -> dict[str, object]:
    matches = [
        entry
        for entry in _entries(client)
        if entry["source_type"] == source_type and entry["source_id"] == source_id
    ]
    assert len(matches) == 1
    return matches[0]


def _lines_by_code(entry: dict[str, object]) -> dict[str, dict[str, object]]:
    lines = entry["lines"]
    assert isinstance(lines, list)
    return {str(line["account_code"]): line for line in lines}


def _pay(
    client: TestClient,
    invoice_id: object,
    amount: str,
    *,
    method: str = "cash",
) -> dict[str, object]:
    response = client.post(
        f"/api/v1/invoices/{invoice_id}/payments",
        headers={"Idempotency-Key": str(uuid4())},
        json={
            "amount": amount,
            "payment_date": date.today().isoformat(),
            "method": method,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def _assert_balanced(entry: dict[str, object], expected: str) -> None:
    assert _money(entry["total_debit"]) == _money(expected)
    assert _money(entry["total_credit"]) == _money(expected)
    assert _money(entry["total_debit"]) == _money(entry["total_credit"])


def test_issue_invoice_generates_balanced_entry(
    client: TestClient,
    db_session: Session,
) -> None:
    invoice = _issue_invoice(client, unit_price="100.00", tax_rate="19")
    entry = _entry_for(client, "INVOICE", invoice["id"])

    assert entry["status"] == "POSTED"
    assert entry["entry_date"] == invoice["issue_date"]
    lines = _lines_by_code(entry)
    assert _money(lines["130505"]["debit"]) == Decimal("119.00")
    assert _money(lines["130505"]["credit"]) == ZERO
    assert _money(lines["413505"]["debit"]) == ZERO
    assert _money(lines["413505"]["credit"]) == Decimal("100.00")
    assert _money(lines["240801"]["debit"]) == ZERO
    assert _money(lines["240801"]["credit"]) == Decimal("19.00")
    _assert_balanced(entry, "119.00")

    entry_id = UUID(str(entry["id"]))
    db_totals = db_session.execute(
        select(
            func.coalesce(func.sum(AccountingEntryLine.debit), 0),
            func.coalesce(func.sum(AccountingEntryLine.credit), 0),
        ).where(AccountingEntryLine.entry_id == entry_id)
    ).one()
    assert _money(db_totals[0]) == Decimal("119.00")
    assert _money(db_totals[1]) == Decimal("119.00")
    assert _money(db_totals[0]) == _money(db_totals[1])


def test_zero_total_invoice_does_not_create_entry(client: TestClient) -> None:
    invoice = _issue_invoice(client, unit_price="0.00", tax_rate="0")

    assert invoice["lifecycle_status"] == "issued"
    assert invoice["total"] == "0.00"
    assert all(entry["source_id"] != invoice["id"] for entry in _entries(client))


def test_payment_generates_balanced_entry(
    client: TestClient,
    db_session: Session,
) -> None:
    invoice = _issue_invoice(client, unit_price="100.00", tax_rate="0")
    payment = _pay(client, invoice["id"], "30.00")

    entry = _entry_for(client, "PAYMENT", payment["id"])
    lines = _lines_by_code(entry)
    assert _money(lines["110505"]["debit"]) == Decimal("30.00")
    assert _money(lines["110505"]["credit"]) == ZERO
    assert _money(lines["130505"]["debit"]) == ZERO
    assert _money(lines["130505"]["credit"]) == Decimal("30.00")
    _assert_balanced(entry, "30.00")

    assert db_session.scalar(select(func.count()).select_from(AccountingEntry)) == 2


def test_void_invoice_generates_reversal_entry(
    client: TestClient,
    db_session: Session,
) -> None:
    invoice = _issue_invoice(client, unit_price="100.00", tax_rate="19")
    original = _entry_for(client, "INVOICE", invoice["id"])

    response = client.post(
        f"/api/v1/invoices/{invoice['id']}/void",
        json={"reason": "Anulación contable"},
    )
    assert response.status_code == 200, response.text

    reversal = _entry_for(client, "VOID", invoice["id"])
    lines = _lines_by_code(reversal)
    assert _money(lines["130505"]["debit"]) == ZERO
    assert _money(lines["130505"]["credit"]) == Decimal("119.00")
    assert _money(lines["413505"]["debit"]) == Decimal("100.00")
    assert _money(lines["413505"]["credit"]) == ZERO
    assert _money(lines["240801"]["debit"]) == Decimal("19.00")
    assert _money(lines["240801"]["credit"]) == ZERO
    _assert_balanced(reversal, "119.00")

    original_after = _entry_for(client, "INVOICE", invoice["id"])
    assert original_after["status"] == "POSTED"
    # El orden de la colección puede variar al recargar la relación; lo
    # relevante es que los movimientos originales no hayan cambiado.
    assert _lines_by_code(original) == _lines_by_code(original_after)
    assert db_session.scalar(select(func.count()).select_from(AccountingEntry)) == 2


def test_delete_payment_generates_reversal_entry(
    client: TestClient,
    db_session: Session,
) -> None:
    invoice = _issue_invoice(client, unit_price="100.00", tax_rate="0")
    payment = _pay(client, invoice["id"], "30.00")

    response = client.delete(f"/api/v1/invoices/{invoice['id']}/payments/{payment['id']}")
    assert response.status_code == 204, response.text

    reversal = _entry_for(client, "PAYMENT_REVERSAL", payment["id"])
    lines = _lines_by_code(reversal)
    assert _money(lines["130505"]["debit"]) == Decimal("30.00")
    assert _money(lines["130505"]["credit"]) == ZERO
    assert _money(lines["110505"]["debit"]) == ZERO
    assert _money(lines["110505"]["credit"]) == Decimal("30.00")
    _assert_balanced(reversal, "30.00")
    assert db_session.scalar(select(func.count()).select_from(AccountingEntry)) == 3


def test_accounts_endpoint_returns_seeded_puc(client: TestClient) -> None:
    response = client.get("/api/v1/accounting/accounts?limit=100")

    assert response.status_code == 200, response.text
    accounts = {account["code"]: account for account in response.json()}
    assert accounts["130505"] == {
        "code": "130505",
        "name": "Clientes nacionales",
        "account_type": "ACTIVO",
        "nature": "DEBITO",
        "parent_code": "1305",
    }
    assert accounts["413505"]["account_type"] == "INGRESO"
    assert accounts["240801"]["account_type"] == "PASIVO"
    assert accounts["110505"]["name"] == "Caja general"
    assert accounts["111005"]["name"] == "Bancos moneda nacional"


def test_entry_detail_and_missing_entry(client: TestClient) -> None:
    invoice = _issue_invoice(client, unit_price="100.00", tax_rate="19")
    entry = _entry_for(client, "INVOICE", invoice["id"])

    detail = client.get(f"/api/v1/accounting/entries/{entry['id']}")
    assert detail.status_code == 200, detail.text
    assert detail.json() == entry

    missing = client.get(f"/api/v1/accounting/entries/{uuid4()}")
    assert missing.status_code == 404
    assert missing.json() == {"detail": "Asiento contable no encontrado"}


def test_payment_is_atomic_if_accounting_fails(
    client: TestClient,
    db_session: Session,
) -> None:
    invoice = _issue_invoice(client, unit_price="100.00", tax_rate="0")
    db_session.execute(delete(AccountingAccount).where(AccountingAccount.code == "110505"))
    db_session.flush()

    with pytest.raises(AccountingError):
        client.post(
            f"/api/v1/invoices/{invoice['id']}/payments",
            headers={"Idempotency-Key": str(uuid4())},
            json={
                "amount": "30.00",
                "payment_date": date.today().isoformat(),
                "method": "cash",
            },
        )

    unchanged = client.get(f"/api/v1/invoices/{invoice['id']}")
    assert unchanged.status_code == 200
    assert _money(unchanged.json()["balance"]) == Decimal("100.00")
    assert unchanged.json()["payment_status"] == "unpaid"
    assert db_session.scalar(select(func.count()).select_from(Payment)) == 0


def test_issue_is_atomic_if_accounting_fails(
    client: TestClient,
    db_session: Session,
) -> None:
    invoice = _create_invoice(client, unit_price="100.00", tax_rate="19")
    db_session.execute(delete(AccountingAccount).where(AccountingAccount.code == "413505"))
    db_session.flush()

    with pytest.raises(AccountingError):
        client.post(f"/api/v1/invoices/{invoice['id']}/issue")

    unchanged = client.get(f"/api/v1/invoices/{invoice['id']}")
    assert unchanged.status_code == 200
    assert unchanged.json()["lifecycle_status"] == "draft"
    assert unchanged.json()["number"] is None
    assert db_session.scalar(select(func.count()).select_from(AccountingEntry)) == 0
