"""Tests de aging de cartera (valores derivados, sin persistencia)."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from typing import Any
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import update
from sqlalchemy.orm import Session

from app.domain.models.invoice import Invoice

TWOPLACES = Decimal("0.01")


def _money(value: object) -> Decimal:
    return Decimal(str(value)).quantize(TWOPLACES)


def _setup_catalog(client: TestClient) -> tuple[str, str]:
    suffix = uuid4().hex[:8].upper()
    contact = client.post(
        "/api/v1/contacts",
        json={"name": f"Cliente Aging {suffix}", "email": f"aging-{suffix}@example.com"},
    )
    assert contact.status_code == 201, contact.text
    item = client.post(
        "/api/v1/items",
        json={
            "name": f"Producto {suffix}",
            "description": "Producto de prueba",
            "unit_price": "1.00",
            "tax_id": None,
        },
    )
    assert item.status_code == 201, item.text
    warehouse = client.post(
        "/api/v1/warehouses",
        json={"name": f"Bodega {suffix}", "code": f"WH{suffix}"},
    )
    assert warehouse.status_code == 201, warehouse.text
    movement = client.post(
        "/api/v1/inventory/movements",
        json={
            "item_id": item.json()["id"],
            "warehouse_id": warehouse.json()["id"],
            "movement_type": "IN",
            "quantity": "500",
        },
    )
    assert movement.status_code == 201, movement.text
    return str(contact.json()["id"]), str(item.json()["id"])


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
    invoice = response.json()
    issued = client.post(f"/api/v1/invoices/{invoice['id']}/issue")
    assert issued.status_code == 200, issued.text
    return issued.json()


def _pay(client: TestClient, invoice_id: str, amount: str) -> None:
    response = client.post(
        f"/api/v1/invoices/{invoice_id}/payments",
        json={
            "amount": amount,
            "payment_date": date.today().isoformat(),
            "method": "Transferencia",
        },
        headers={"Idempotency-Key": str(uuid4())},
    )
    assert response.status_code == 201, response.text


def _aging(client: TestClient, as_of: date) -> dict[str, Any]:
    response = client.get(
        "/api/v1/receivables/aging",
        params={"as_of_date": as_of.isoformat()},
    )
    assert response.status_code == 200, response.text
    return response.json()


def _row_for(report: dict[str, Any], contact_id: str) -> dict[str, Any] | None:
    for row in report["by_customer"]:
        if row["contact_id"] == contact_id:
            return row
    return None


def test_fully_paid_invoice_is_excluded(client: TestClient) -> None:
    contact_id, item_id = _setup_catalog(client)
    today = date(2026, 10, 25)
    invoice = _create_invoice(
        client,
        contact_id=contact_id,
        item_id=item_id,
        total="150000.00",
        issue_date=today - timedelta(days=40),
        due_date=today - timedelta(days=10),
    )
    _pay(client, str(invoice["id"]), "150000.00")

    report = _aging(client, today)
    assert _row_for(report, contact_id) is None
    assert _money(report["buckets_totals"]["total"]) == _money("0.00")


def test_future_due_date_is_current(client: TestClient) -> None:
    contact_id, item_id = _setup_catalog(client)
    today = date(2026, 10, 25)
    _create_invoice(
        client,
        contact_id=contact_id,
        item_id=item_id,
        total="100000.00",
        issue_date=today,
        due_date=today + timedelta(days=15),
    )

    row = _row_for(_aging(client, today), contact_id)
    assert row is not None
    assert _money(row["current"]) == _money("100000.00")
    assert row["invoice_count"] == 1


def test_bucket_boundaries(client: TestClient) -> None:
    contact_id, item_id = _setup_catalog(client)
    today = date(2026, 10, 25)
    for days, amount in ((10, "10000.00"), (45, "20000.00"), (100, "30000.00"), (150, "40000.00")):
        _create_invoice(
            client,
            contact_id=contact_id,
            item_id=item_id,
            total=amount,
            issue_date=today - timedelta(days=days),
            due_date=today - timedelta(days=days),
        )

    row = _row_for(_aging(client, today), contact_id)
    assert row is not None
    assert _money(row["d0_30"]) == _money("10000.00")
    assert _money(row["d31_60"]) == _money("20000.00")
    assert _money(row["d91_120"]) == _money("30000.00")
    assert _money(row["d120_plus"]) == _money("40000.00")
    assert _money(row["total"]) == _money("100000.00")
    assert row["invoice_count"] == 4


def test_multiple_invoices_same_customer_aggregate(client: TestClient) -> None:
    contact_id, item_id = _setup_catalog(client)
    today = date(2026, 10, 25)
    for amount in ("10000.00", "25000.00"):
        _create_invoice(
            client,
            contact_id=contact_id,
            item_id=item_id,
            total=amount,
            issue_date=today - timedelta(days=5),
            due_date=today - timedelta(days=5),
        )

    report = _aging(client, today)
    row = _row_for(report, contact_id)
    assert row is not None
    assert _money(row["d0_30"]) == _money("35000.00")
    assert row["invoice_count"] == 2
    assert _money(report["buckets_totals"]["total"]) == _money("35000.00")
    assert _money(report["total_overdue"]) == _money("35000.00")


def test_multiple_customers_totals(client: TestClient) -> None:
    first_contact, item_id = _setup_catalog(client)
    suffix = uuid4().hex[:8].upper()
    second = client.post(
        "/api/v1/contacts",
        json={"name": f"Cliente Aging {suffix}", "email": f"aging2-{suffix}@example.com"},
    )
    assert second.status_code == 201, second.text
    second_contact = str(second.json()["id"])
    today = date(2026, 10, 25)
    _create_invoice(
        client,
        contact_id=first_contact,
        item_id=item_id,
        total="30000.00",
        issue_date=today,
        due_date=today + timedelta(days=5),
    )
    _create_invoice(
        client,
        contact_id=second_contact,
        item_id=item_id,
        total="45000.00",
        issue_date=today - timedelta(days=70),
        due_date=today - timedelta(days=70),
    )

    report = _aging(client, today)
    assert _money(report["buckets_totals"]["current"]) == _money("30000.00")
    assert _money(report["buckets_totals"]["d61_90"]) == _money("45000.00")
    assert _money(report["buckets_totals"]["total"]) == _money("75000.00")
    assert _money(report["total_overdue"]) == _money("45000.00")
    assert len(report["by_customer"]) == 2


def test_missing_due_date_falls_back_to_issue_date_plus_30(
    client: TestClient,
    db_session: Session,
) -> None:
    contact_id, item_id = _setup_catalog(client)
    issue_date = date(2026, 9, 1)
    invoice = _create_invoice(
        client,
        contact_id=contact_id,
        item_id=item_id,
        total="12000.00",
        issue_date=issue_date,
        due_date=issue_date + timedelta(days=30),
    )
    db_session.execute(update(Invoice).where(Invoice.id == invoice["id"]).values(due_date=None))
    db_session.flush()

    # 30 días después de la emisión: aún corriente.
    current_report = _aging(client, issue_date + timedelta(days=30))
    row = _row_for(current_report, contact_id)
    assert row is not None
    assert _money(row["current"]) == _money("12000.00")

    # 45 días después: 15 días vencidos → d0_30.
    overdue_report = _aging(client, issue_date + timedelta(days=45))
    row = _row_for(overdue_report, contact_id)
    assert row is not None
    assert _money(row["d0_30"]) == _money("12000.00")


def test_summary_top_customers(client: TestClient) -> None:
    today = date(2026, 10, 25)
    first_contact, item_id = _setup_catalog(client)
    suffix = uuid4().hex[:8].upper()
    second = client.post(
        "/api/v1/contacts",
        json={"name": f"Cliente Aging {suffix}", "email": f"aging3-{suffix}@example.com"},
    )
    assert second.status_code == 201, second.text
    second_contact = str(second.json()["id"])
    _create_invoice(
        client,
        contact_id=first_contact,
        item_id=item_id,
        total="10000.00",
        issue_date=today - timedelta(days=40),
        due_date=today - timedelta(days=40),
    )
    _create_invoice(
        client,
        contact_id=second_contact,
        item_id=item_id,
        total="90000.00",
        issue_date=today - timedelta(days=40),
        due_date=today - timedelta(days=40),
    )

    response = client.get(
        "/api/v1/receivables/summary",
        params={"as_of_date": today.isoformat()},
    )
    assert response.status_code == 200, response.text
    summary = response.json()
    assert summary["top_customers"][0]["contact_id"] == second_contact
    assert _money(summary["total_overdue"]) == _money("100000.00")
    assert summary["customer_count"] == 2
