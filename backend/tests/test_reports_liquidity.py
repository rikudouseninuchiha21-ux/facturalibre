"""Tests de cartera (aging) y flujo de caja."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from typing import Any
from uuid import uuid4

from fastapi.testclient import TestClient

TWOPLACES = Decimal("0.01")


def _money(value: object) -> Decimal:
    return Decimal(str(value)).quantize(TWOPLACES)


def _previous_month_start(today: date) -> date:
    if today.month == 1:
        return date(today.year - 1, 12, 1)
    return date(today.year, today.month - 1, 1)


def _create_contact(
    client: TestClient,
    *,
    name: str,
    contact_type: str = "customer",
) -> str:
    response = client.post(
        "/api/v1/contacts",
        json={
            "name": name,
            "email": f"{uuid4()}@example.com",
            "type": contact_type,
        },
    )
    assert response.status_code == 201, response.text
    return str(response.json()["id"])


def _setup_sales_catalog(client: TestClient) -> tuple[str, str]:
    item = client.post(
        "/api/v1/items",
        json={
            "name": f"Producto liquidez {uuid4().hex}",
            "description": "Producto para reportes",
            "unit_price": "100.00",
            "tax_id": None,
        },
    )
    assert item.status_code == 201, item.text

    warehouse = client.post(
        "/api/v1/warehouses",
        json={"name": f"Bodega liquidez {uuid4().hex}", "code": uuid4().hex[:12]},
    )
    assert warehouse.status_code == 201, warehouse.text

    movement = client.post(
        "/api/v1/inventory/movements",
        json={
            "item_id": item.json()["id"],
            "warehouse_id": warehouse.json()["id"],
            "movement_type": "IN",
            "quantity": "30",
        },
    )
    assert movement.status_code == 201, movement.text
    return str(item.json()["id"]), str(warehouse.json()["id"])


def _create_invoice(
    client: TestClient,
    *,
    contact_id: str,
    item_id: str,
    total: str,
    issue_date: date,
    due_date: date,
) -> dict[str, Any]:
    response = client.post(
        "/api/v1/invoices",
        json={
            "contact_id": contact_id,
            "issue_date": issue_date.isoformat(),
            "due_date": due_date.isoformat(),
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
    return response.json()


def _issue_invoice(client: TestClient, invoice_id: object) -> dict[str, Any]:
    response = client.post(f"/api/v1/invoices/{invoice_id}/issue")
    assert response.status_code == 200, response.text
    return response.json()


def _create_issued_invoice(
    client: TestClient,
    *,
    contact_id: str,
    item_id: str,
    total: str,
    issue_date: date,
    due_date: date,
) -> dict[str, Any]:
    invoice = _create_invoice(
        client,
        contact_id=contact_id,
        item_id=item_id,
        total=total,
        issue_date=issue_date,
        due_date=due_date,
    )
    return _issue_invoice(client, invoice["id"])


def _pay_invoice(
    client: TestClient,
    invoice_id: object,
    amount: str,
    payment_date: date,
) -> None:
    response = client.post(
        f"/api/v1/invoices/{invoice_id}/payments",
        json={
            "amount": amount,
            "payment_date": payment_date.isoformat(),
            "method": "Transferencia",
        },
        headers={"Idempotency-Key": str(uuid4())},
    )
    assert response.status_code == 201, response.text


def _create_purchase(
    client: TestClient,
    *,
    supplier_id: str,
    issue_date: date,
    due_date: date,
) -> dict[str, Any]:
    response = client.post(
        "/api/v1/purchases",
        json={
            "supplier_id": supplier_id,
            "issue_date": issue_date.isoformat(),
            "due_date": due_date.isoformat(),
            "lines": [
                {
                    "description": "Compra para flujo de caja",
                    "quantity": "1",
                    "unit_cost": "200.00",
                    "tax_rate": "0",
                }
            ],
        },
        headers={"Idempotency-Key": str(uuid4())},
    )
    assert response.status_code == 201, response.text
    return response.json()


def _pay_purchase(
    client: TestClient,
    purchase_id: object,
    amount: str,
    payment_date: date,
) -> None:
    response = client.post(
        f"/api/v1/purchases/{purchase_id}/payments",
        json={
            "amount": amount,
            "payment_date": payment_date.isoformat(),
            "method": "Transferencia",
        },
        headers={"Idempotency-Key": str(uuid4())},
    )
    assert response.status_code == 201, response.text


def _create_expense(
    client: TestClient,
    *,
    expense_date: date,
    amount: str,
) -> None:
    response = client.post(
        "/api/v1/expenses",
        json={
            "date": expense_date.isoformat(),
            "concept": "Gasto para flujo de caja",
            "amount": amount,
            "payment_method": "cash",
        },
    )
    assert response.status_code == 201, response.text


def _create_bank_account(
    client: TestClient,
    *,
    account_number: str,
    accounting_account_code: str = "111005",
) -> str:
    response = client.post(
        "/api/v1/treasury/accounts",
        json={
            "name": f"Cuenta {account_number}",
            "bank_name": "Bancolombia",
            "account_number": account_number,
            "account_type": "CHECKING",
            "accounting_account_code": accounting_account_code,
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
    counterpart_account_code: str | None = None,
    counterpart_account_id: str | None = None,
) -> None:
    payload: dict[str, object] = {
        "transaction_type": transaction_type,
        "date": transaction_date.isoformat(),
        "amount": amount,
        "description": "Movimiento para flujo de caja",
    }
    if counterpart_account_code is not None:
        payload["counterpart_account_code"] = counterpart_account_code
    if counterpart_account_id is not None:
        payload["counterpart_account_id"] = counterpart_account_id

    response = client.post(
        f"/api/v1/treasury/accounts/{account_id}/transactions",
        json=payload,
    )
    assert response.status_code == 201, response.text


def test_aging_report_groups_receivables_by_overdue_range(
    client: TestClient,
) -> None:
    item_id, _ = _setup_sales_catalog(client)
    client_a = _create_contact(client, name="Cliente Aging A")
    client_b = _create_contact(client, name="Cliente Aging B")
    today = date.today()

    _create_issued_invoice(
        client,
        contact_id=client_a,
        item_id=item_id,
        total="100.00",
        issue_date=today - timedelta(days=40),
        due_date=today - timedelta(days=10),
    )
    _create_issued_invoice(
        client,
        contact_id=client_a,
        item_id=item_id,
        total="100.00",
        issue_date=today - timedelta(days=150),
        due_date=today - timedelta(days=120),
    )
    _create_issued_invoice(
        client,
        contact_id=client_b,
        item_id=item_id,
        total="100.00",
        issue_date=today - timedelta(days=75),
        due_date=today - timedelta(days=45),
    )
    _create_issued_invoice(
        client,
        contact_id=client_b,
        item_id=item_id,
        total="100.00",
        issue_date=today - timedelta(days=105),
        due_date=today - timedelta(days=75),
    )

    response = client.get("/api/v1/reports/aging")

    assert response.status_code == 200, response.text
    report = response.json()
    assert report["as_of"] == today.isoformat()
    assert _money(report["total_receivable"]) == Decimal("400.00")

    buckets = {bucket["key"]: bucket for bucket in report["buckets"]}
    assert [bucket["key"] for bucket in report["buckets"]] == [
        "0_30",
        "31_60",
        "61_90",
        "over_90",
    ]
    for key in ("0_30", "31_60", "61_90", "over_90"):
        assert _money(buckets[key]["total"]) == Decimal("100.00")
        assert buckets[key]["invoice_count"] == 1

    clients = {row["contact_id"]: row for row in report["clients"]}
    assert len(clients) == 2

    row_a = clients[client_a]
    assert _money(row_a["total_balance"]) == Decimal("200.00")
    assert row_a["max_days_overdue"] == 120
    assert row_a["oldest_due_date"] == (today - timedelta(days=120)).isoformat()
    assert _money(row_a["buckets"]["0_30"]) == Decimal("100.00")
    assert _money(row_a["buckets"]["over_90"]) == Decimal("100.00")
    assert _money(row_a["buckets"]["31_60"]) == Decimal("0.00")

    row_b = clients[client_b]
    assert _money(row_b["total_balance"]) == Decimal("200.00")
    assert row_b["max_days_overdue"] == 75
    assert _money(row_b["buckets"]["31_60"]) == Decimal("100.00")
    assert _money(row_b["buckets"]["61_90"]) == Decimal("100.00")


def test_cash_flow_report_aggregates_sources_and_projects_collections(
    client: TestClient,
) -> None:
    item_id, _ = _setup_sales_catalog(client)
    customer_id = _create_contact(client, name="Cliente Flujo")
    supplier_id = _create_contact(
        client,
        name="Proveedor Flujo",
        contact_type="supplier",
    )
    today = date.today()
    previous_month = _previous_month_start(today)

    # Venta cobrada parcialmente. Su vencimiento queda fuera de la proyección
    # de 30 días para aislar el cálculo de la cartera pendiente.
    sale = _create_issued_invoice(
        client,
        contact_id=customer_id,
        item_id=item_id,
        total="100.00",
        issue_date=today,
        due_date=today + timedelta(days=60),
    )
    _pay_invoice(client, sale["id"], "40.00", today)

    purchase = _create_purchase(
        client,
        supplier_id=supplier_id,
        issue_date=today,
        due_date=today + timedelta(days=30),
    )
    issued_purchase = client.post(f"/api/v1/purchases/{purchase['id']}/issue")
    assert issued_purchase.status_code == 200, issued_purchase.text
    _pay_purchase(client, purchase["id"], "50.00", today)

    _create_expense(client, expense_date=today, amount="30.00")
    _create_expense(client, expense_date=previous_month, amount="15.00")

    account_id = _create_bank_account(
        client,
        account_number=uuid4().hex[:12],
    )
    destination_id = _create_bank_account(
        client,
        account_number=uuid4().hex[:12],
        accounting_account_code="11100501",
    )
    _create_bank_transaction(
        client,
        account_id,
        transaction_type="DEPOSIT",
        amount="25.00",
        transaction_date=today,
        counterpart_account_code="413505",
    )
    _create_bank_transaction(
        client,
        account_id,
        transaction_type="WITHDRAWAL",
        amount="10.00",
        transaction_date=today,
        counterpart_account_code="5199",
    )
    _create_bank_transaction(
        client,
        account_id,
        transaction_type="TRANSFER",
        amount="5.00",
        transaction_date=today,
        counterpart_account_id=destination_id,
    )

    # Cartera para la proyección: una factura vence en 10 días, otra en 40 y
    # una tercera ya está vencida.
    _create_issued_invoice(
        client,
        contact_id=customer_id,
        item_id=item_id,
        total="80.00",
        issue_date=today,
        due_date=today + timedelta(days=10),
    )
    _create_issued_invoice(
        client,
        contact_id=customer_id,
        item_id=item_id,
        total="20.00",
        issue_date=today,
        due_date=today + timedelta(days=40),
    )
    _create_issued_invoice(
        client,
        contact_id=customer_id,
        item_id=item_id,
        total="50.00",
        issue_date=today - timedelta(days=35),
        due_date=today - timedelta(days=5),
    )

    response = client.get("/api/v1/reports/cash-flow")

    assert response.status_code == 200, response.text
    report = response.json()
    assert report["as_of"] == today.isoformat()
    assert len(report["months"]) == 6

    months = {month["month"]: month for month in report["months"]}
    current_key = f"{today.year:04d}-{today.month:02d}"
    previous_key = f"{previous_month.year:04d}-{previous_month.month:02d}"

    current = months[current_key]
    assert _money(current["income"]) == Decimal("65.00")
    assert _money(current["expenses"]) == Decimal("90.00")
    assert _money(current["net"]) == Decimal("-25.00")
    assert _money(current["income_sources"]["customer_payments"]) == Decimal("40.00")
    assert _money(current["income_sources"]["bank_deposits"]) == Decimal("25.00")
    assert _money(current["expense_sources"]["supplier_payments"]) == Decimal("50.00")
    assert _money(current["expense_sources"]["expenses"]) == Decimal("30.00")
    assert _money(current["expense_sources"]["bank_withdrawals"]) == Decimal("10.00")

    previous = months[previous_key]
    assert _money(previous["income"]) == Decimal("0.00")
    assert _money(previous["expenses"]) == Decimal("15.00")
    assert _money(previous["net"]) == Decimal("-15.00")

    projection = report["projection"]
    assert projection["horizon_days"] == 30
    assert _money(projection["due_within_30_days"]) == Decimal("80.00")
    assert _money(projection["overdue_balance"]) == Decimal("50.00")
    assert _money(projection["expected_collections"]) == Decimal("130.00")
    assert projection["invoice_count"] == 2


def test_liquidity_reports_require_authentication(
    anonymous_client: TestClient,
) -> None:
    assert anonymous_client.get("/api/v1/reports/aging").status_code == 401
    assert anonymous_client.get("/api/v1/reports/cash-flow").status_code == 401
