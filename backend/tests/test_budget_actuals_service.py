"""Tests del reporte Presupuesto vs Real (gasto derivado de la contabilidad)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.domain.models.accounting import (
    AccountingEntry,
    AccountingEntryLine,
    AccountingEntryStatus,
    AccountingSourceType,
)

ZERO = Decimal("0.00")
TWOPLACES = Decimal("0.01")


def _money(value: object) -> Decimal:
    return Decimal(str(value)).quantize(TWOPLACES)


def _create_cost_center(client: TestClient) -> dict[str, Any]:
    response = client.post(
        "/api/v1/cost-centers",
        json={"code": f"CC-{uuid4().hex[:8].upper()}", "name": "Actuals"},
    )
    assert response.status_code == 201, response.text
    return response.json()


def _post_manual_entry(
    db_session: Session,
    *,
    entry_date: date,
    cost_center_id: UUID | None,
    debit_account: str,
    credit_account: str,
    amount: Decimal,
) -> None:
    """Crea un asiento manual balanceado, opcionalmente etiquetado."""
    entry = AccountingEntry(
        entry_date=entry_date,
        description=f"Asiento manual {debit_account}",
        source_type=AccountingSourceType.INVOICE,
        source_id=uuid4(),
        status=AccountingEntryStatus.POSTED,
        lines=[
            AccountingEntryLine(
                account_code=debit_account,
                debit=amount,
                credit=ZERO,
                cost_center_id=cost_center_id,
            ),
            AccountingEntryLine(
                account_code=credit_account,
                debit=ZERO,
                credit=amount,
                cost_center_id=cost_center_id,
            ),
        ],
    )
    db_session.add(entry)
    db_session.flush()


def _setup_budget(
    client: TestClient,
    *,
    year: int,
    month: int,
) -> dict[str, Any]:
    center = _create_cost_center(client)
    budget = client.post(
        "/api/v1/budgets",
        json={
            "cost_center_id": center["id"],
            "period_year": year,
            "period_month": month,
        },
    )
    assert budget.status_code == 201, budget.text
    budget = budget.json()

    for account_code, amount in (("5199", "1000.00"), ("6135", "500.00")):
        line = client.post(
            f"/api/v1/budgets/{budget['id']}/lines",
            json={"account_code": account_code, "amount": amount},
        )
        assert line.status_code == 201, line.text
    return budget


def test_budget_vs_actual_math(client: TestClient, db_session: Session) -> None:
    """actual = SUM(debit - credit) del mes y del centro; variance y variance_pct."""
    today = date.today()
    budget = _setup_budget(client, year=today.year, month=today.month)
    center_id = UUID(str(budget["cost_center"]["id"]))

    # Dentro del mes y del centro: cuentan.
    _post_manual_entry(
        db_session,
        entry_date=date(today.year, today.month, 10),
        cost_center_id=center_id,
        debit_account="5199",
        credit_account="110505",
        amount=Decimal("300.00"),
    )
    _post_manual_entry(
        db_session,
        entry_date=date(today.year, today.month, 12),
        cost_center_id=center_id,
        debit_account="6135",
        credit_account="1435",
        amount=Decimal("200.00"),
    )
    # Fuera del mes (mes siguiente): no cuentan.
    next_year, next_month = (
        (today.year + 1, 1) if today.month == 12 else (today.year, today.month + 1)
    )
    _post_manual_entry(
        db_session,
        entry_date=date(next_year, next_month, 5),
        cost_center_id=center_id,
        debit_account="5199",
        credit_account="110505",
        amount=Decimal("999.00"),
    )
    # Dentro del mes pero SIN centro de costo: no cuentan.
    _post_manual_entry(
        db_session,
        entry_date=date(today.year, today.month, 15),
        cost_center_id=None,
        debit_account="5199",
        credit_account="110505",
        amount=Decimal("777.00"),
    )

    response = client.get(f"/api/v1/budgets/{budget['id']}/actuals")
    assert response.status_code == 200, response.text
    report = response.json()

    lines = {line["account_code"]: line for line in report["lines"]}
    assert _money(lines["5199"]["budgeted"]) == Decimal("1000.00")
    assert _money(lines["5199"]["actual"]) == Decimal("300.00")
    assert _money(lines["5199"]["variance"]) == Decimal("-700.00")
    assert _money(lines["5199"]["variance_pct"]) == Decimal("-70.00")

    assert _money(lines["6135"]["budgeted"]) == Decimal("500.00")
    assert _money(lines["6135"]["actual"]) == Decimal("200.00")
    assert _money(lines["6135"]["variance"]) == Decimal("-300.00")
    assert _money(lines["6135"]["variance_pct"]) == Decimal("-60.00")

    totals = report["totals"]
    assert _money(totals["budgeted"]) == Decimal("1500.00")
    assert _money(totals["actual"]) == Decimal("500.00")
    assert _money(totals["variance"]) == Decimal("-1000.00")
    assert _money(totals["variance_pct"]) == Decimal("-66.67")


def test_budgeted_zero_returns_null_variance_pct(
    client: TestClient,
    db_session: Session,
) -> None:
    """Cuenta presupuestada en cero: variance 0 y variance_pct None."""
    today = date.today()
    center = _create_cost_center(client)
    budget = client.post(
        "/api/v1/budgets",
        json={
            "cost_center_id": center["id"],
            "period_year": today.year,
            "period_month": today.month,
        },
    )
    assert budget.status_code == 201, budget.text
    budget = budget.json()

    line = client.post(
        f"/api/v1/budgets/{budget['id']}/lines",
        json={"account_code": "5160", "amount": "0.00"},
    )
    assert line.status_code == 201, line.text

    _post_manual_entry(
        db_session,
        entry_date=date(today.year, today.month, 8),
        cost_center_id=UUID(str(center["id"])),
        debit_account="5160",
        credit_account="1592",
        amount=Decimal("80.00"),
    )

    response = client.get(f"/api/v1/budgets/{budget['id']}/actuals")
    assert response.status_code == 200, response.text
    report = response.json()

    assert len(report["lines"]) == 1
    zero_line = report["lines"][0]
    assert _money(zero_line["budgeted"]) == ZERO
    assert _money(zero_line["actual"]) == Decimal("80.00")
    assert _money(zero_line["variance"]) == Decimal("80.00")
    assert zero_line["variance_pct"] is None

    assert report["totals"]["variance_pct"] is None


def test_aggregated_report_groups_by_cost_center(
    client: TestClient,
    db_session: Session,
) -> None:
    """GET /reports/budget-vs-actual devuelve un bloque por presupuesto del periodo."""
    today = date.today()
    budget = _setup_budget(client, year=today.year, month=today.month)
    _setup_budget(client, year=today.year, month=today.month)

    response = client.get(
        f"/api/v1/reports/budget-vs-actual?period_year={today.year}&period_month={today.month}"
    )
    assert response.status_code == 200, response.text
    report = response.json()

    assert report["period_year"] == today.year
    assert report["period_month"] == today.month
    assert len(report["blocks"]) == 2
    budget_ids = {block["budget_id"] for block in report["blocks"]}
    assert budget["id"] in budget_ids

    filtered = client.get(
        "/api/v1/reports/budget-vs-actual"
        f"?period_year={today.year}&period_month={today.month}"
        f"&cost_center_id={budget['cost_center']['id']}"
    )
    assert len(filtered.json()["blocks"]) == 1

    empty = client.get("/api/v1/reports/budget-vs-actual?period_year=2031&period_month=6")
    assert empty.status_code == 200, empty.text
    assert empty.json()["blocks"] == []
