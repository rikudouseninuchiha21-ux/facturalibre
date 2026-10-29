"""Pruebas de exportación CSV de los estados financieros."""

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


def test_export_income_statement_csv(client: TestClient, db_session: Session) -> None:
    _post_entry(
        db_session,
        date(2026, 3, 2),
        "Ingreso exportación",
        [("110505", D("1000.00"), D("0.00")), ("4135", D("0.00"), D("1000.00"))],
    )
    _post_entry(
        db_session,
        date(2026, 3, 3),
        "Gasto exportación",
        [("510506", D("250.00"), D("0.00")), ("110505", D("0.00"), D("250.00"))],
    )

    response = client.get(
        "/api/v1/reports/export/csv",
        params={
            "report": "income-statement",
            "from_date": "2026-03-01",
            "to_date": "2026-03-31",
        },
    )
    assert response.status_code == 200, response.text
    assert response.headers["content-type"].startswith("text/csv")
    assert 'filename="estado-resultados.csv"' in response.headers["content-disposition"]

    text = response.content.decode("utf-8-sig")
    lines = text.splitlines()
    assert lines[0] == "Tipo,Código,Cuenta,Saldo"
    assert any(line.startswith("Ingreso,4135,") and line.endswith(",1000.00") for line in lines)
    assert any(
        line.startswith("Gasto/Costo,510506,") and line.endswith(",250.00") for line in lines
    )
    assert "UTILIDAD NETA,,,750.00" in lines


def test_export_balance_sheet_csv(client: TestClient, db_session: Session) -> None:
    _post_entry(
        db_session,
        date(2026, 3, 2),
        "Ingreso balance",
        [("110505", D("500.00"), D("0.00")), ("4135", D("0.00"), D("500.00"))],
    )

    response = client.get(
        "/api/v1/reports/export/csv",
        params={
            "report": "balance-sheet",
            "as_of_date": "2026-03-31",
        },
    )
    assert response.status_code == 200, response.text
    assert 'filename="balance-general.csv"' in response.headers["content-disposition"]
    text = response.content.decode("utf-8-sig")
    assert text.splitlines()[0] == "Tipo,Código,Cuenta,Saldo"
    assert "TOTAL ACTIVO,,,500.00" in text
    assert "TOTAL PATRIMONIO,,,500.00" in text
