"""Tests de los estados financieros NIIF (Fase 39C)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy.orm import Session

from app.application.accounting.niif_reports import NiifReportsService
from app.domain.models.accounting import (
    AccountingEntry,
    AccountingEntryLine,
    AccountingEntryStatus,
    AccountingSourceType,
)

FROM = date(2026, 1, 1)
TO = date(2026, 1, 31)
D = Decimal


def _post_entry(
    db: Session,
    entry_date: date,
    description: str,
    lines: list[tuple[str, Decimal, Decimal]],
) -> None:
    """Asiento POSTED balanceado: (código, débito, crédito)."""
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


@pytest.fixture
def niif_books(db_session: Session) -> Session:
    """Libros de prueba: capital antes del periodo; venta, costo y gasto dentro.

    - Aporte de capital 2.000.000 (antes de FROM).
    - Venta 1.000.000 cobrada en efectivo (110505 / 4135).
    - Costo de ventas 400.000 (6135 / 110505).
    - Gasto de administración 100.000 (510506 / 110505).
    """
    _post_entry(
        db_session,
        date(2025, 12, 15),
        "Aporte inicial de capital",
        [("110505", D("2000000.00"), D(0)), ("3105", D(0), D("2000000.00"))],
    )
    _post_entry(
        db_session,
        date(2026, 1, 10),
        "Venta del periodo",
        [("110505", D("1000000.00"), D(0)), ("4135", D(0), D("1000000.00"))],
    )
    _post_entry(
        db_session,
        date(2026, 1, 12),
        "Costo de la venta",
        [("6135", D("400000.00"), D(0)), ("110505", D(0), D("400000.00"))],
    )
    _post_entry(
        db_session,
        date(2026, 1, 20),
        "Gasto de administración",
        [("510506", D("100000.00"), D(0)), ("110505", D(0), D("100000.00"))],
    )
    return db_session


def test_income_statement_niif(niif_books: Session) -> None:
    statement = NiifReportsService(niif_books).income_statement_niif(from_date=FROM, to_date=TO)
    assert statement["revenue"] == D("1000000.00")
    assert statement["cost_of_sales"] == D("400000.00")
    assert statement["gross_profit"] == D("600000.00")
    assert statement["total_expenses"] == D("500000.00")
    # Ganancia neta = 1.000.000 - 400.000 - 100.000 (gastos administración).
    assert statement["net_income"] == D("500000.00")
    # Las secciones NIIF están completas y en orden.
    labels = [section["label"] for section in statement["sections"]]
    assert labels[0] == "Ingresos de actividades ordinarias"
    assert labels[2] == "Ganancia bruta"
    assert labels[-1] == "Ganancia neta del ejercicio"


def test_balance_sheet_niif_equation(niif_books: Session) -> None:
    balance = NiifReportsService(niif_books).balance_sheet_niif(as_of_date=TO)
    # Activo = efectivo 2.500.000. Patrimonio = capital 2.000.000 +
    # resultado del ejercicio 500.000. Pasivo = 0.
    assert balance["total_assets"] == D("2500000.00")
    assert balance["total_liabilities"] == D("0.00")
    assert balance["equity"] == D("2000000.00")
    assert balance["period_result"] == D("500000.00")
    assert balance["total_equity"] == D("2500000.00")
    assert balance["difference"] == D("0.00")
    assert balance["total_assets"] == balance["total_liabilities"] + balance["total_equity"]
    assert balance["asset_composition"]["cash"] == D("2500000.00")
    assert any(account["code"] == "110505" for account in balance["asset_accounts"])


def test_cash_flow_niif_matches_bank(niif_books: Session) -> None:
    flow = NiifReportsService(niif_books).cash_flow_niif(from_date=FROM, to_date=TO)
    assert flow["net_income"] == D("500000.00")
    assert flow["opening_cash"] == D("2000000.00")
    assert flow["operating_cash_flow"] == D("500000.00")
    assert flow["investing_cash_flow"] == D("0.00")
    assert flow["financing_cash_flow"] == D("0.00")
    assert flow["net_cash_change"] == D("500000.00")
    # El saldo final calculado coincide con el saldo en bancos (PUC 11).
    assert flow["closing_cash"] == D("2500000.00")
    assert flow["bank_closing_cash"] == D("2500000.00")
    assert flow["closing_cash"] == flow["bank_closing_cash"]


def test_balance_sheet_stays_balanced_with_liabilities(niif_books: Session) -> None:
    """Asientos con pasivos: la ecuación Activo = Pasivo + Patrimonio se mantiene.

    Con partida doble un descuadre es imposible por diseño; el servicio
    vigila la ecuación y lanza ``TreasuryError`` con el descuadre exacto si
    alguna clasificación PUC quedara fuera de las clases 1-6.
    """
    _post_entry(
        niif_books,
        date(2026, 1, 25),
        "Compra a crédito de proveedores",
        [("510506", D("100000.00"), D(0)), ("220505", D(0), D("100000.00"))],
    )
    balance = NiifReportsService(niif_books).balance_sheet_niif(as_of_date=TO)
    assert balance["total_liabilities"] == D("100000.00")
    # Activo 2.500.000 = Pasivo 100.000 + Patrimonio (capital 2.000.000
    # + resultado del ejercicio 400.000).
    assert balance["total_equity"] == D("2400000.00")
    assert balance["difference"] == D("0.00")
    assert balance["total_assets"] == balance["total_liabilities"] + balance["total_equity"]
