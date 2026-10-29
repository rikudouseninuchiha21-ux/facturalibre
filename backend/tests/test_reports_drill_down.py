"""Pruebas del auxiliar (drill-down) de cuentas contables."""

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
from app.domain.models.company import Company

D = Decimal


def _post_entry(
    db: Session,
    *,
    entry_date: date,
    description: str,
    lines: list[tuple[str, Decimal, Decimal]],
    company_id=None,
) -> None:
    entry = AccountingEntry(
        company_id=company_id,
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
                company_id=company_id,
                entry_id=entry.id,
                account_code=code,
                debit=debit,
                credit=credit,
            )
        )
    db.flush()


def test_drill_down_returns_account_movements(
    client: TestClient,
    db_session: Session,
) -> None:
    _post_entry(
        db_session,
        entry_date=date(2026, 1, 5),
        description="Cobro inicial",
        lines=[("110505", D("100.00"), D("0.00")), ("4135", D("0.00"), D("100.00"))],
    )
    _post_entry(
        db_session,
        entry_date=date(2026, 1, 10),
        description="Pago de gasto",
        lines=[("510506", D("30.00"), D("0.00")), ("110505", D("0.00"), D("30.00"))],
    )

    response = client.get(
        "/api/v1/reports/drill-down",
        params={
            "account_code": "110505",
            "from_date": "2026-01-01",
            "to_date": "2026-01-31",
        },
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["account_code"] == "110505"
    assert data["closing_balance"] == "70.00"
    assert len(data["movements"]) == 2
    assert data["movements"][0]["entry_number"].startswith("AS-")
    assert data["movements"][0]["debit"] == "100.00"
    assert data["movements"][1]["credit"] == "30.00"
    assert data["movements"][1]["balance"] == "70.00"


def test_drill_down_isolated_by_company(client: TestClient, db_session: Session) -> None:
    _post_entry(
        db_session,
        entry_date=date(2026, 1, 5),
        description="Movimiento empresa A",
        lines=[("110505", D("100.00"), D("0.00")), ("4135", D("0.00"), D("100.00"))],
    )

    company_b = Company(name="Empresa Drill B S.A.S.", tax_id="901555444-3")
    db_session.add(company_b)
    db_session.flush()
    _post_entry(
        db_session,
        entry_date=date(2026, 1, 6),
        description="Movimiento empresa B",
        lines=[("110505", D("900.00"), D("0.00")), ("4135", D("0.00"), D("900.00"))],
        company_id=company_b.id,
    )

    response = client.get(
        "/api/v1/reports/drill-down",
        params={
            "account_code": "110505",
            "from_date": "2026-01-01",
            "to_date": "2026-01-31",
        },
    )
    assert response.status_code == 200, response.text
    descriptions = [movement["description"] for movement in response.json()["movements"]]
    assert descriptions == ["Movimiento empresa A"]
    assert response.json()["closing_balance"] == "100.00"
