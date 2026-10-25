"""Tests del módulo de gastos: asiento automático, borrado y reversión."""

from __future__ import annotations

from decimal import Decimal
from typing import Any
from uuid import uuid4

from fastapi.testclient import TestClient

TWOPLACES = Decimal("0.01")


def _money(value: object) -> Decimal:
    return Decimal(str(value)).quantize(TWOPLACES)


def _create_expense(
    client: TestClient,
    *,
    amount: str = "150000.00",
    payment_method: str = "cash",
) -> Any:
    return client.post(
        "/api/v1/expenses",
        json={
            "date": "2026-10-24",
            "concept": "Arriendo de oficina",
            "amount": amount,
            "payment_method": payment_method,
            "reference": "FC-001",
        },
    )


def _entry_for(
    client: TestClient,
    source_type: str,
    source_id: object,
) -> dict[str, Any]:
    response = client.get("/api/v1/accounting/entries?limit=100")
    assert response.status_code == 200, response.text
    matches = [
        entry
        for entry in response.json()
        if entry["source_type"] == source_type and entry["source_id"] == source_id
    ]
    assert len(matches) == 1
    return matches[0]


def _lines_by_code(entry: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {str(line["account_code"]): line for line in entry["lines"]}


def test_create_expense_generates_cash_entry(client: TestClient) -> None:
    response = _create_expense(client)
    assert response.status_code == 201, response.text
    expense = response.json()

    assert _money(expense["amount"]) == Decimal("150000.00")
    assert expense["version"] == 1

    entry = _entry_for(client, "EXPENSE", expense["id"])
    lines = _lines_by_code(entry)
    assert _money(lines["5199"]["debit"]) == Decimal("150000.00")
    assert _money(lines["5199"]["credit"]) == Decimal("0.00")
    assert _money(lines["110505"]["debit"]) == Decimal("0.00")
    assert _money(lines["110505"]["credit"]) == Decimal("150000.00")
    assert _money(entry["total_debit"]) == _money(entry["total_credit"])


def test_create_expense_with_transfer_uses_bank_account(client: TestClient) -> None:
    response = _create_expense(client, payment_method="transfer")
    assert response.status_code == 201, response.text
    expense = response.json()

    entry = _entry_for(client, "EXPENSE", expense["id"])
    lines = _lines_by_code(entry)
    assert _money(lines["5199"]["debit"]) == Decimal("150000.00")
    assert _money(lines["111005"]["credit"]) == Decimal("150000.00")


def test_expense_amount_must_be_positive(client: TestClient) -> None:
    response = _create_expense(client, amount="0.00")
    assert response.status_code == 422, response.text


def test_delete_expense_creates_reversal_entry(client: TestClient) -> None:
    created = _create_expense(client)
    assert created.status_code == 201, created.text
    expense_id = created.json()["id"]

    deleted = client.delete(f"/api/v1/expenses/{expense_id}")
    assert deleted.status_code == 204, deleted.text

    listed = client.get("/api/v1/expenses")
    assert listed.status_code == 200
    assert all(expense["id"] != expense_id for expense in listed.json())

    reversal = _entry_for(client, "EXPENSE_REVERSAL", expense_id)
    lines = _lines_by_code(reversal)
    assert _money(lines["5199"]["debit"]) == Decimal("0.00")
    assert _money(lines["5199"]["credit"]) == Decimal("150000.00")
    assert _money(lines["110505"]["debit"]) == Decimal("150000.00")
    assert _money(lines["110505"]["credit"]) == Decimal("0.00")


def test_delete_missing_expense_returns_404(client: TestClient) -> None:
    response = client.delete(f"/api/v1/expenses/{uuid4()}")
    assert response.status_code == 404, response.text
