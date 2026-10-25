"""Tests de bancos y tesorería: cuentas, movimientos, contabilidad y conciliación."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from fastapi.testclient import TestClient

TWOPLACES = Decimal("0.01")


def _money(value: object) -> Decimal:
    return Decimal(str(value)).quantize(TWOPLACES)


def _create_account(
    client: TestClient,
    *,
    name: str = "Cuenta principal",
    bank_name: str = "Bancolombia",
    account_number: str = "123456789",
    accounting_account_code: str = "111005",
) -> Any:
    return client.post(
        "/api/v1/treasury/accounts",
        json={
            "name": name,
            "bank_name": bank_name,
            "account_number": account_number,
            "account_type": "CHECKING",
            "accounting_account_code": accounting_account_code,
        },
    )


def _create_transaction(
    client: TestClient,
    account_id: str,
    *,
    transaction_type: str,
    amount: str,
    counterpart_account_code: str | None = None,
    counterpart_account_id: str | None = None,
    description: str = "Movimiento de prueba",
) -> Any:
    payload: dict[str, object] = {
        "transaction_type": transaction_type,
        "date": "2026-10-24",
        "amount": amount,
        "description": description,
    }
    if counterpart_account_code is not None:
        payload["counterpart_account_code"] = counterpart_account_code
    if counterpart_account_id is not None:
        payload["counterpart_account_id"] = counterpart_account_id

    return client.post(
        f"/api/v1/treasury/accounts/{account_id}/transactions",
        json=payload,
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


def test_create_bank_account(client: TestClient) -> None:
    response = _create_account(client)
    assert response.status_code == 201, response.text
    account = response.json()

    assert account["name"] == "Cuenta principal"
    assert account["accounting_account_code"] == "111005"
    assert account["accounting_account_name"] == "Bancos moneda nacional"
    assert _money(account["balance"]) == Decimal("0.00")
    assert account["is_active"] is True
    assert account["version"] == 1


def test_duplicate_bank_account_returns_409(client: TestClient) -> None:
    first = _create_account(client)
    assert first.status_code == 201, first.text

    duplicate = _create_account(client, name="Otra cuenta")
    assert duplicate.status_code == 409, duplicate.text


def test_bank_account_requires_available_puc_account(client: TestClient) -> None:
    response = _create_account(client, accounting_account_code="413505")
    assert response.status_code == 422, response.text


def test_deposit_generates_balanced_entry_and_balance(client: TestClient) -> None:
    account = _create_account(client)
    assert account.status_code == 201, account.text
    account_id = account.json()["id"]

    deposit = _create_transaction(
        client,
        account_id,
        transaction_type="DEPOSIT",
        amount="1000.00",
        counterpart_account_code="413505",
    )
    assert deposit.status_code == 201, deposit.text
    transaction = deposit.json()

    assert transaction["transaction_type"] == "DEPOSIT"
    assert transaction["bank_account_name"] == "Cuenta principal"
    assert transaction["is_reconciled"] is False

    entry = _entry_for(client, "BANK_TRANSACTION", transaction["id"])
    lines = _lines_by_code(entry)
    assert _money(lines["111005"]["debit"]) == Decimal("1000.00")
    assert _money(lines["413505"]["credit"]) == Decimal("1000.00")

    account_after = client.get(f"/api/v1/treasury/accounts/{account_id}")
    assert account_after.status_code == 200
    data = account_after.json()
    assert _money(data["balance"]) == Decimal("1000.00")
    assert _money(data["unreconciled_balance"]) == Decimal("1000.00")
    assert data["unreconciled_transactions"] == 1


def test_withdrawal_generates_entry_and_reduces_balance(client: TestClient) -> None:
    account = _create_account(client)
    account_id = account.json()["id"]

    assert (
        _create_transaction(
            client,
            account_id,
            transaction_type="DEPOSIT",
            amount="500.00",
            counterpart_account_code="413505",
        ).status_code
        == 201
    )

    withdrawal = _create_transaction(
        client,
        account_id,
        transaction_type="WITHDRAWAL",
        amount="200.00",
        counterpart_account_code="5199",
    )
    assert withdrawal.status_code == 201, withdrawal.text
    transaction = withdrawal.json()

    entry = _entry_for(client, "BANK_TRANSACTION", transaction["id"])
    lines = _lines_by_code(entry)
    assert _money(lines["5199"]["debit"]) == Decimal("200.00")
    assert _money(lines["111005"]["credit"]) == Decimal("200.00")

    account_after = client.get(f"/api/v1/treasury/accounts/{account_id}")
    assert _money(account_after.json()["balance"]) == Decimal("300.00")


def test_transfer_between_accounts_generates_one_entry(client: TestClient) -> None:
    source = _create_account(client)
    destination = _create_account(
        client,
        name="Cuenta secundaria",
        bank_name="Davivienda",
        account_number="987654321",
        accounting_account_code="11100501",
    )
    assert source.status_code == 201, source.text
    assert destination.status_code == 201, destination.text
    source_id = source.json()["id"]
    destination_id = destination.json()["id"]

    assert (
        _create_transaction(
            client,
            source_id,
            transaction_type="DEPOSIT",
            amount="500.00",
            counterpart_account_code="413505",
        ).status_code
        == 201
    )

    transfer = _create_transaction(
        client,
        source_id,
        transaction_type="TRANSFER",
        amount="200.00",
        counterpart_account_id=destination_id,
        description="Traslado a cuenta secundaria",
    )
    assert transfer.status_code == 201, transfer.text
    transaction = transfer.json()

    assert transaction["counterpart_account_id"] == destination_id
    assert transaction["counterpart_account_name"] == "Cuenta secundaria"

    entry = _entry_for(client, "BANK_TRANSACTION", transaction["id"])
    lines = _lines_by_code(entry)
    assert _money(lines["11100501"]["debit"]) == Decimal("200.00")
    assert _money(lines["111005"]["credit"]) == Decimal("200.00")

    source_after = client.get(f"/api/v1/treasury/accounts/{source_id}")
    destination_after = client.get(f"/api/v1/treasury/accounts/{destination_id}")
    assert _money(source_after.json()["balance"]) == Decimal("300.00")
    assert _money(destination_after.json()["balance"]) == Decimal("200.00")

    # La transferencia recibida aparece en el libro de la cuenta destino.
    destination_transactions = client.get(
        f"/api/v1/treasury/accounts/{destination_id}/transactions"
    )
    assert destination_transactions.status_code == 200
    assert len(destination_transactions.json()) == 1


def test_transfer_with_same_puc_account_returns_422(client: TestClient) -> None:
    source = _create_account(client)
    destination = _create_account(
        client,
        name="Cuenta espejo",
        bank_name="Banco de Bogotá",
        account_number="555555",
        accounting_account_code="111005",
    )
    assert source.status_code == 201, source.text
    assert destination.status_code == 201, destination.text

    transfer = _create_transaction(
        client,
        source.json()["id"],
        transaction_type="TRANSFER",
        amount="100.00",
        counterpart_account_id=destination.json()["id"],
    )
    assert transfer.status_code == 422, transfer.text


def test_reconcile_and_unreconcile_transaction(client: TestClient) -> None:
    account = _create_account(client)
    account_id = account.json()["id"]
    deposit = _create_transaction(
        client,
        account_id,
        transaction_type="DEPOSIT",
        amount="100.00",
        counterpart_account_code="413505",
    )
    assert deposit.status_code == 201, deposit.text
    transaction = deposit.json()

    reconciled = client.post(
        f"/api/v1/treasury/transactions/{transaction['id']}/reconcile",
        json={"version": transaction["version"]},
    )
    assert reconciled.status_code == 200, reconciled.text
    assert reconciled.json()["is_reconciled"] is True
    assert reconciled.json()["reconciled_at"] is not None
    assert reconciled.json()["version"] == 2

    account_after = client.get(f"/api/v1/treasury/accounts/{account_id}")
    assert _money(account_after.json()["reconciled_balance"]) == Decimal("100.00")
    assert _money(account_after.json()["unreconciled_balance"]) == Decimal("0.00")
    assert account_after.json()["unreconciled_transactions"] == 0

    unreconciled = client.post(
        f"/api/v1/treasury/transactions/{transaction['id']}/unreconcile",
        json={"version": 2},
    )
    assert unreconciled.status_code == 200, unreconciled.text
    assert unreconciled.json()["is_reconciled"] is False
    assert unreconciled.json()["reconciled_at"] is None
    assert unreconciled.json()["version"] == 3


def test_reconcile_with_stale_version_returns_409(client: TestClient) -> None:
    account = _create_account(client)
    deposit = _create_transaction(
        client,
        account.json()["id"],
        transaction_type="DEPOSIT",
        amount="50.00",
        counterpart_account_code="413505",
    )
    assert deposit.status_code == 201, deposit.text
    transaction = deposit.json()

    first = client.post(
        f"/api/v1/treasury/transactions/{transaction['id']}/reconcile",
        json={"version": transaction["version"]},
    )
    assert first.status_code == 200, first.text

    stale = client.post(
        f"/api/v1/treasury/transactions/{transaction['id']}/reconcile",
        json={"version": transaction["version"]},
    )
    assert stale.status_code == 409, stale.text


def test_inactive_account_rejects_new_transactions(client: TestClient) -> None:
    account = _create_account(client)
    account_id = account.json()["id"]

    deactivated = client.patch(
        f"/api/v1/treasury/accounts/{account_id}",
        json={"is_active": False, "version": 1},
    )
    assert deactivated.status_code == 200, deactivated.text
    assert deactivated.json()["is_active"] is False

    movement = _create_transaction(
        client,
        account_id,
        transaction_type="DEPOSIT",
        amount="10.00",
        counterpart_account_code="413505",
    )
    assert movement.status_code == 409, movement.text


def test_treasury_summary_totals(client: TestClient) -> None:
    first = _create_account(client)
    second = _create_account(
        client,
        name="Cuenta secundaria",
        bank_name="Davivienda",
        account_number="222222",
        accounting_account_code="11100501",
    )
    assert first.status_code == 201, first.text
    assert second.status_code == 201, second.text

    assert (
        _create_transaction(
            client,
            first.json()["id"],
            transaction_type="DEPOSIT",
            amount="700.00",
            counterpart_account_code="413505",
        ).status_code
        == 201
    )
    assert (
        _create_transaction(
            client,
            second.json()["id"],
            transaction_type="DEPOSIT",
            amount="300.00",
            counterpart_account_code="413505",
        ).status_code
        == 201
    )

    summary = client.get("/api/v1/treasury/summary")
    assert summary.status_code == 200, summary.text
    data = summary.json()
    assert _money(data["total_balance"]) == Decimal("1000.00")
    assert _money(data["total_unreconciled_balance"]) == Decimal("1000.00")
    assert data["total_accounts"] == 2
    assert data["active_accounts"] == 2
    assert data["unreconciled_transactions"] == 2


def test_puc_catalog_is_available_to_treasury(client: TestClient) -> None:
    response = client.get("/api/v1/treasury/puc-accounts")
    assert response.status_code == 200, response.text

    codes = {account["code"] for account in response.json()}
    assert {"111005", "11100501", "5199"} <= codes
