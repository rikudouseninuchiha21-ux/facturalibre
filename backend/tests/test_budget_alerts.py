"""Tests de los niveles de alerta de sobregiro presupuestal."""

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
        json={"code": f"CC-{uuid4().hex[:8].upper()}", "name": "Alertas"},
    )
    assert response.status_code == 201, response.text
    return response.json()


def _post_manual_entry(
    db_session: Session,
    *,
    entry_date: date,
    cost_center_id: UUID,
    debit_account: str,
    amount: Decimal,
) -> None:
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
                account_code="110505",
                debit=ZERO,
                credit=amount,
                cost_center_id=cost_center_id,
            ),
        ],
    )
    db_session.add(entry)
    db_session.flush()


def _make_budget(
    client: TestClient,
    db_session: Session,
    *,
    budgeted: str,
    actual: str,
    year: int,
    month: int,
    approve: bool = True,
    account_code: str = "5199",
) -> dict[str, Any]:
    """Crea un centro, su presupuesto de una línea y el gasto real indicado."""
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

    line = client.post(
        f"/api/v1/budgets/{budget['id']}/lines",
        json={"account_code": account_code, "amount": budgeted},
    )
    assert line.status_code == 201, line.text

    if _money(actual) > ZERO:
        _post_manual_entry(
            db_session,
            entry_date=date(year, month, 10),
            cost_center_id=UUID(center["id"]),
            debit_account=account_code,
            amount=Decimal(actual),
        )

    if approve:
        approved = client.post(f"/api/v1/budgets/{budget['id']}/approve")
        assert approved.status_code == 200, approved.text

    report = client.get(f"/api/v1/budgets/{budget['id']}/actuals")
    assert report.status_code == 200, report.text
    return report.json()


def test_alert_level_ok(client: TestClient, db_session: Session) -> None:
    """50% de utilización → OK, sin alertas."""
    today = date.today()
    report = _make_budget(
        client,
        db_session,
        budgeted="100000.00",
        actual="50000.00",
        year=today.year,
        month=today.month,
    )

    line = report["lines"][0]
    assert _money(line["utilization_pct"]) == Decimal("50.00")
    assert line["alert_level"] == "OK"
    assert _money(report["totals"]["utilization_pct_total"]) == Decimal("50.00")
    assert report["totals"]["alert_level_total"] == "OK"
    assert report["has_alerts"] is False


def test_alert_level_warning(client: TestClient, db_session: Session) -> None:
    """85% de utilización → WARNING."""
    today = date.today()
    report = _make_budget(
        client,
        db_session,
        budgeted="100000.00",
        actual="85000.00",
        year=today.year,
        month=today.month,
    )

    line = report["lines"][0]
    assert _money(line["utilization_pct"]) == Decimal("85.00")
    assert line["alert_level"] == "WARNING"
    assert report["totals"]["alert_level_total"] == "WARNING"
    assert report["has_alerts"] is True


def test_alert_level_critical(client: TestClient, db_session: Session) -> None:
    """95% de utilización → CRITICAL."""
    today = date.today()
    report = _make_budget(
        client,
        db_session,
        budgeted="100000.00",
        actual="95000.00",
        year=today.year,
        month=today.month,
    )

    line = report["lines"][0]
    assert _money(line["utilization_pct"]) == Decimal("95.00")
    assert line["alert_level"] == "CRITICAL"
    assert report["totals"]["alert_level_total"] == "CRITICAL"


def test_alert_level_over(client: TestClient, db_session: Session) -> None:
    """110% de utilización → OVER (sobregiro)."""
    today = date.today()
    report = _make_budget(
        client,
        db_session,
        budgeted="100000.00",
        actual="110000.00",
        year=today.year,
        month=today.month,
    )

    line = report["lines"][0]
    assert _money(line["utilization_pct"]) == Decimal("110.00")
    assert line["alert_level"] == "OVER"
    assert report["totals"]["alert_level_total"] == "OVER"
    assert report["has_alerts"] is True


def test_budgeted_zero_is_not_applicable(
    client: TestClient,
    db_session: Session,
) -> None:
    """Presupuesto en cero → N/A y utilization None, sin ZeroDivisionError.

    Un presupuesto con total cero no puede aprobarse (regla de la fase 34),
    pero el reporte de actuals se calcula igual en cualquier estado.
    """
    today = date.today()
    report = _make_budget(
        client,
        db_session,
        budgeted="0.00",
        actual="80000.00",
        year=today.year,
        month=today.month,
        approve=False,
    )

    line = report["lines"][0]
    assert line["utilization_pct"] is None
    assert line["alert_level"] == "N/A"
    assert report["totals"]["utilization_pct_total"] is None
    assert report["totals"]["alert_level_total"] == "N/A"


def test_line_alerts_independent_of_total(
    client: TestClient,
    db_session: Session,
) -> None:
    """Las alertas de línea y de total se calculan por separado."""
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

    # Línea 5199: 100000 presupuestado, 50000 real → OK (50%).
    # Línea 6135: 100000 presupuestado, 110000 real → OVER (110%).
    for account_code, amount in (("5199", "100000.00"), ("6135", "100000.00")):
        line = client.post(
            f"/api/v1/budgets/{budget['id']}/lines",
            json={"account_code": account_code, "amount": amount},
        )
        assert line.status_code == 201, line.text

    center_id = UUID(center["id"])
    _post_manual_entry(
        db_session,
        entry_date=date(today.year, today.month, 10),
        cost_center_id=center_id,
        debit_account="5199",
        amount=Decimal("50000.00"),
    )
    _post_manual_entry(
        db_session,
        entry_date=date(today.year, today.month, 12),
        cost_center_id=center_id,
        debit_account="6135",
        amount=Decimal("110000.00"),
    )

    report = client.get(f"/api/v1/budgets/{budget['id']}/actuals")
    assert report.status_code == 200, report.text
    report = report.json()

    lines = {line["account_code"]: line for line in report["lines"]}
    assert lines["5199"]["alert_level"] == "OK"
    assert _money(lines["5199"]["utilization_pct"]) == Decimal("50.00")
    assert lines["6135"]["alert_level"] == "OVER"
    assert _money(lines["6135"]["utilization_pct"]) == Decimal("110.00")

    # Total: 200000 presupuestado, 160000 ejecutado → 80% → WARNING.
    assert _money(report["totals"]["budgeted"]) == Decimal("200000.00")
    assert _money(report["totals"]["actual"]) == Decimal("160000.00")
    assert _money(report["totals"]["utilization_pct_total"]) == Decimal("80.00")
    assert report["totals"]["alert_level_total"] == "WARNING"
    assert report["has_alerts"] is True
