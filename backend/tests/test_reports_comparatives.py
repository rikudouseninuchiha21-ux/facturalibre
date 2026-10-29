"""Pruebas de comparativos periodo actual vs periodo anterior."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.domain.models.accounting import (
    AccountingEntry,
    AccountingEntryLine,
    AccountingEntryStatus,
    AccountingSourceType,
)

D = Decimal


def _post_entry(
    db: Session,
    entry_date: date,
    description: str,
    lines: list[tuple[str, Decimal, Decimal]],
) -> None:
    entry = AccountingEntry(
        entry_date=entry_date,
        description=description,
        source_type=AccountingSourceType.EXPENSE,
        source_id=uuid4(),
        status=AccountingEntryStatus.POSTED,
    )
    db.add(entry)
    db.flush()
    for code, debit, credit in lines:
        db.add(
            AccountingEntryLine(
                entry_id=entry.id,
                account_code=code,
                debit=debit,
                credit=credit,
            )
        )
    db.flush()


def _seed_two_periods(db: Session) -> None:
    # Periodo actual: 2026-02-01 a 2026-02-10.
    _post_entry(
        db,
        date(2026, 2, 2),
        "Ingreso actual",
        [("110505", D("1000.00"), D("0.00")), ("4135", D("0.00"), D("1000.00"))],
    )
    _post_entry(
        db,
        date(2026, 2, 3),
        "Gasto actual",
        [("510506", D("400.00"), D("0.00")), ("110505", D("0.00"), D("400.00"))],
    )
    # Periodo anterior comparable: 2026-01-22 a 2026-01-31.
    _post_entry(
        db,
        date(2026, 1, 25),
        "Ingreso anterior",
        [("110505", D("800.00"), D("0.00")), ("4135", D("0.00"), D("800.00"))],
    )
    _post_entry(
        db,
        date(2026, 1, 26),
        "Gasto anterior",
        [("510506", D("300.00"), D("0.00")), ("110505", D("0.00"), D("300.00"))],
    )


def test_income_statement_compare_with_previous(
    client: TestClient,
    db_session: Session,
) -> None:
    _seed_two_periods(db_session)

    response = client.get(
        "/api/v1/reports/income-statement",
        params={
            "start_date": "2026-02-01",
            "end_date": "2026-02-10",
            "compare_with_previous": "true",
        },
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["total_income"] == "1000.00"
    assert data["total_expenses"] == "400.00"
    assert data["net_income"] == "600.00"

    previous = data["previous_period"]
    assert previous is not None
    assert previous["start_date"] == "2026-01-22"
    assert previous["end_date"] == "2026-01-31"
    assert previous["total_income"] == "800.00"
    assert previous["total_expenses"] == "300.00"
    assert previous["net_income"] == "500.00"


def test_balance_sheet_compare_with_previous(
    client: TestClient,
    db_session: Session,
) -> None:
    _seed_two_periods(db_session)

    response = client.get(
        "/api/v1/reports/balance-sheet",
        params={
            "as_of_date": "2026-02-10",
            "from_date": "2026-01-01",
            "compare_with_previous": "true",
        },
    )
    assert response.status_code == 200, response.text
    data = response.json()
    previous = data["previous_period"]
    assert previous is not None
    assert previous["as_of_date"] == "2025-12-31"
    assert previous["total_assets"] == "0.00"
    assert previous["total_liabilities"] == "0.00"
    assert previous["total_equity"] == "0.00"
    assert previous["balanced"] is True
