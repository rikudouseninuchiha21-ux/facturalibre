"""Tests de conciliación bancaria y su efecto en el flujo de caja."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from typing import Any
from uuid import uuid4

from fastapi.testclient import TestClient

TWOPLACES = Decimal("0.01")


def _money(value: object) -> Decimal:
    return Decimal(str(value)).quantize(TWOPLACES)


def _create_contact(client: TestClient, *, name: str) -> str:
    response = client.post(
        "/api/v1/contacts",
        json={
            "name": name,
            "email": f"{uuid4()}@example.com",
            "type": "customer",
        },
    )
    assert response.status_code == 201, response.text
    return str(response.json()["id"])


def _setup_sales_catalog(client: TestClient) -> str:
    item = client.post(
        "/api/v1/items",
        json={
            "name": f"Producto conciliación {uuid4().hex}",
            "description": "Producto para conciliación",
            "unit_price": "100.00",
            "tax_id": None,
        },
    )
    assert item.status_code == 201, item.text

    warehouse = client.post(
        "/api/v1/warehouses",
        json={"name": f"Bodega conciliación {uuid4().hex}", "code": uuid4().hex[:12]},
    )
    assert warehouse.status_code == 201, warehouse.text

    movement = client.post(
        "/api/v1/inventory/movements",
        json={
            "item_id": item.json()["id"],
            "warehouse_id": warehouse.json()["id"],
            "movement_type": "IN",
            "quantity": "10",
        },
    )
    assert movement.status_code == 201, movement.text
    return str(item.json()["id"])


def _create_issued_invoice(
    client: TestClient,
    *,
    contact_id: str,
    item_id: str,
    total: str,
    issue_date: date,
) -> dict[str, Any]:
    response = client.post(
        "/api/v1/invoices",
        json={
            "contact_id": contact_id,
            "issue_date": issue_date.isoformat(),
            "due_date": (issue_date + timedelta(days=30)).isoformat(),
            "currency": "COP",
            "lines": [
                {
                    "item_id": item_id,
                    "quantity": "1",
                    "unit_price": total,
                    "discount_percent": "0",
                }
            ],
        },
        headers={"Idempotency-Key": str(uuid4())},
    )
    assert response.status_code == 201, response.text
    invoice = response.json()
    issued = client.post(f"/api/v1/invoices/{invoice['id']}/issue")
    assert issued.status_code == 200, issued.text
    return issued.json()


def _pay_invoice(
    client: TestClient,
    invoice_id: object,
    *,
    amount: str,
    payment_date: date,
) -> dict[str, Any]:
    response = client.post(
        f"/api/v1/invoices/{invoice_id}/payments",
        json={
            "amount": amount,
            "payment_date": payment_date.isoformat(),
            "method": "Transferencia",
            "reference": "TRX-CONCILIACION",
        },
        headers={"Idempotency-Key": str(uuid4())},
    )
    assert response.status_code == 201, response.text
    return response.json()


def _create_expense(
    client: TestClient,
    *,
    expense_date: date,
    amount: str,
) -> dict[str, Any]:
    response = client.post(
        "/api/v1/expenses",
        json={
            "date": expense_date.isoformat(),
            "concept": "Gasto para conciliación",
            "amount": amount,
            "payment_method": "Transferencia",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def _create_bank_account(client: TestClient) -> str:
    response = client.post(
        "/api/v1/treasury/accounts",
        json={
            "name": "Cuenta conciliación",
            "bank_name": "Bancolombia",
            "account_number": uuid4().hex[:12],
            "account_type": "CHECKING",
            "accounting_account_code": "111005",
        },
    )
    assert response.status_code == 201, response.text
    return str(response.json()["id"])


def _create_bank_transaction(
    client: TestClient,
    account_id: str,
    *,
    transaction_type: str,
    amount: str,
    transaction_date: date,
    counterpart_account_code: str,
) -> dict[str, Any]:
    response = client.post(
        f"/api/v1/treasury/accounts/{account_id}/transactions",
        json={
            "transaction_type": transaction_type,
            "date": transaction_date.isoformat(),
            "amount": amount,
            "description": "Movimiento para conciliación",
            "counterpart_account_code": counterpart_account_code,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def _candidates(client: TestClient, account_id: str) -> dict[str, Any]:
    response = client.get(f"/api/v1/banks/{account_id}/reconciliation-candidates")
    assert response.status_code == 200, response.text
    return response.json()


def _reconcile(
    client: TestClient,
    account_id: str,
    *,
    bank_movement_id: object,
    transaction_id: object,
) -> Any:
    return client.post(
        f"/api/v1/banks/{account_id}/reconcile",
        json={
            "bank_movement_id": str(bank_movement_id),
            "transaction_id": str(transaction_id),
        },
    )


def test_candidates_and_reconcile_payment(client: TestClient) -> None:
    item_id = _setup_sales_catalog(client)
    contact_id = _create_contact(client, name="Cliente Conciliación")
    today = date.today()
    invoice = _create_issued_invoice(
        client,
        contact_id=contact_id,
        item_id=item_id,
        total="40.00",
        issue_date=today,
    )
    payment = _pay_invoice(client, invoice["id"], amount="40.00", payment_date=today)
    account_id = _create_bank_account(client)
    deposit = _create_bank_transaction(
        client,
        account_id,
        transaction_type="DEPOSIT",
        amount="40.00",
        transaction_date=today,
        counterpart_account_code="413505",
    )

    data = _candidates(client, account_id)
    assert data["bank_account_id"] == account_id
    assert len(data["bank_movements"]) == 1
    movement = data["bank_movements"][0]
    assert movement["id"] == deposit["id"]
    assert movement["transaction_type"] == "DEPOSIT"
    assert _money(movement["amount"]) == Decimal("40.00")
    assert len(movement["candidates"]) == 1
    candidate = movement["candidates"][0]
    assert candidate["id"] == payment["id"]
    assert candidate["kind"] == "payment"
    assert candidate["invoice_number"] == invoice["number"]
    assert candidate["party_name"] == "Cliente Conciliación"

    reconciled = _reconcile(
        client,
        account_id,
        bank_movement_id=deposit["id"],
        transaction_id=payment["id"],
    )
    assert reconciled.status_code == 200, reconciled.text
    result = reconciled.json()
    assert result["bank_movement_id"] == deposit["id"]
    assert result["transaction"]["id"] == payment["id"]
    assert result["transaction"]["kind"] == "payment"
    assert result["is_reconciled"] is True
    assert result["reconciled_at"] is not None

    payments = client.get(f"/api/v1/invoices/{invoice['id']}/payments")
    assert payments.status_code == 200, payments.text
    assert payments.json()[0]["bank_movement_id"] == deposit["id"]

    transactions = client.get(
        f"/api/v1/treasury/accounts/{account_id}/transactions"
    )
    assert transactions.status_code == 200, transactions.text
    assert transactions.json()[0]["is_reconciled"] is True

    assert _candidates(client, account_id)["bank_movements"] == []

    # El mismo movimiento no puede conciliarse dos veces.
    duplicate = _reconcile(
        client,
        account_id,
        bank_movement_id=deposit["id"],
        transaction_id=payment["id"],
    )
    assert duplicate.status_code == 409, duplicate.text

    # Desmarcar la conciliación también libera el vínculo del pago.
    unreconciled = client.post(
        f"/api/v1/treasury/transactions/{deposit['id']}/unreconcile",
        json={"version": 2},
    )
    assert unreconciled.status_code == 200, unreconciled.text
    assert unreconciled.json()["is_reconciled"] is False

    payments = client.get(f"/api/v1/invoices/{invoice['id']}/payments")
    assert payments.status_code == 200, payments.text
    assert payments.json()[0]["bank_movement_id"] is None

    candidates_again = _candidates(client, account_id)
    assert len(candidates_again["bank_movements"]) == 1
    assert candidates_again["bank_movements"][0]["id"] == deposit["id"]
    assert candidates_again["bank_movements"][0]["candidates"][0]["id"] == payment["id"]


def test_candidates_and_reconcile_expense(client: TestClient) -> None:
    today = date.today()
    expense = _create_expense(client, expense_date=today, amount="30.00")
    account_id = _create_bank_account(client)
    withdrawal = _create_bank_transaction(
        client,
        account_id,
        transaction_type="WITHDRAWAL",
        amount="30.00",
        transaction_date=today,
        counterpart_account_code="5199",
    )

    data = _candidates(client, account_id)
    movement = data["bank_movements"][0]
    assert movement["id"] == withdrawal["id"]
    assert len(movement["candidates"]) == 1
    candidate = movement["candidates"][0]
    assert candidate["id"] == expense["id"]
    assert candidate["kind"] == "expense"
    assert candidate["description"] == "Gasto para conciliación"

    reconciled = _reconcile(
        client,
        account_id,
        bank_movement_id=withdrawal["id"],
        transaction_id=expense["id"],
    )
    assert reconciled.status_code == 200, reconciled.text
    assert reconciled.json()["transaction"]["kind"] == "expense"

    expenses = client.get("/api/v1/expenses?limit=100")
    assert expenses.status_code == 200, expenses.text
    stored = next(row for row in expenses.json() if row["id"] == expense["id"])
    assert stored["bank_movement_id"] == withdrawal["id"]

    unreconciled = client.post(
        f"/api/v1/treasury/transactions/{withdrawal['id']}/unreconcile",
        json={"version": 2},
    )
    assert unreconciled.status_code == 200, unreconciled.text
    expenses = client.get("/api/v1/expenses?limit=100")
    stored = next(row for row in expenses.json() if row["id"] == expense["id"])
    assert stored["bank_movement_id"] is None


def test_reconcile_rejects_amount_and_date_mismatches(client: TestClient) -> None:
    item_id = _setup_sales_catalog(client)
    contact_id = _create_contact(client, name="Cliente Fuera de Ventana")
    today = date.today()
    invoice = _create_issued_invoice(
        client,
        contact_id=contact_id,
        item_id=item_id,
        total="60.00",
        issue_date=today,
    )
    payment = _pay_invoice(
        client,
        invoice["id"],
        amount="60.00",
        payment_date=today - timedelta(days=4),
    )
    account_id = _create_bank_account(client)
    deposit = _create_bank_transaction(
        client,
        account_id,
        transaction_type="DEPOSIT",
        amount="50.00",
        transaction_date=today,
        counterpart_account_code="413505",
    )

    # El pago no aparece como candidato: ni el monto ni la fecha coinciden.
    assert _candidates(client, account_id)["bank_movements"][0]["candidates"] == []

    mismatch = _reconcile(
        client,
        account_id,
        bank_movement_id=deposit["id"],
        transaction_id=payment["id"],
    )
    assert mismatch.status_code == 422, mismatch.text

    # Aun con el monto correcto, una diferencia de 4 días excede la ventana.
    deposit_2 = _create_bank_transaction(
        client,
        account_id,
        transaction_type="DEPOSIT",
        amount="60.00",
        transaction_date=today,
        counterpart_account_code="413505",
    )
    outside_window = _reconcile(
        client,
        account_id,
        bank_movement_id=deposit_2["id"],
        transaction_id=payment["id"],
    )
    assert outside_window.status_code == 422, outside_window.text


def test_cash_flow_excludes_only_linked_bank_movements(client: TestClient) -> None:
    item_id = _setup_sales_catalog(client)
    contact_id = _create_contact(client, name="Cliente Flujo Conciliado")
    today = date.today()
    invoice = _create_issued_invoice(
        client,
        contact_id=contact_id,
        item_id=item_id,
        total="40.00",
        issue_date=today,
    )
    payment = _pay_invoice(client, invoice["id"], amount="40.00", payment_date=today)
    expense = _create_expense(client, expense_date=today, amount="30.00")

    account_id = _create_bank_account(client)
    linked_deposit = _create_bank_transaction(
        client,
        account_id,
        transaction_type="DEPOSIT",
        amount="40.00",
        transaction_date=today,
        counterpart_account_code="413505",
    )
    _create_bank_transaction(
        client,
        account_id,
        transaction_type="DEPOSIT",
        amount="10.00",
        transaction_date=today,
        counterpart_account_code="413505",
    )
    linked_withdrawal = _create_bank_transaction(
        client,
        account_id,
        transaction_type="WITHDRAWAL",
        amount="30.00",
        transaction_date=today,
        counterpart_account_code="5199",
    )
    _create_bank_transaction(
        client,
        account_id,
        transaction_type="WITHDRAWAL",
        amount="5.00",
        transaction_date=today,
        counterpart_account_code="5199",
    )

    assert (
        _reconcile(
            client,
            account_id,
            bank_movement_id=linked_deposit["id"],
            transaction_id=payment["id"],
        ).status_code
        == 200
    )
    assert (
        _reconcile(
            client,
            account_id,
            bank_movement_id=linked_withdrawal["id"],
            transaction_id=expense["id"],
        ).status_code
        == 200
    )

    response = client.get("/api/v1/reports/cash-flow")
    assert response.status_code == 200, response.text
    months = {
        month["month"]: month
        for month in response.json()["months"]
    }
    current = months[f"{today.year:04d}-{today.month:02d}"]

    # El pago y el gasto siguen siendo la fuente primaria; solo se excluyen
    # los movimientos bancarios que quedaron vinculados.
    assert _money(current["income"]) == Decimal("50.00")
    assert _money(current["income_sources"]["customer_payments"]) == Decimal("40.00")
    assert _money(current["income_sources"]["bank_deposits"]) == Decimal("10.00")
    assert _money(current["expenses"]) == Decimal("35.00")
    assert _money(current["expense_sources"]["expenses"]) == Decimal("30.00")
    assert _money(current["expense_sources"]["bank_withdrawals"]) == Decimal("5.00")


def test_reconciliation_endpoints_require_authentication(
    anonymous_client: TestClient,
) -> None:
    account_id = uuid4()
    assert (
        anonymous_client.get(
            f"/api/v1/banks/{account_id}/reconciliation-candidates"
        ).status_code
        == 401
    )
    assert (
        anonymous_client.post(
            f"/api/v1/banks/{account_id}/reconcile",
            json={
                "bank_movement_id": str(uuid4()),
                "transaction_id": str(uuid4()),
            },
        ).status_code
        == 401
    )
