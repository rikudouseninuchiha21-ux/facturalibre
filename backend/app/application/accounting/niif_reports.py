"""Estados financieros NIIF (Fase 39C).

Agrupa los saldos PUC en las estructuras de presentación NIIF:
Estado de Resultados por función, Balance General con clasificación
Corriente/No Corriente y Flujo de Efectivo por método indirecto.

Todo con ``Decimal``. Los saldos derivan exclusivamente de los asientos
POSTED: no existe ninguna tabla de saldos persistida.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.domain.exceptions import TreasuryError
from app.domain.models.accounting import (
    AccountingAccount,
    AccountingEntry,
    AccountingEntryLine,
    AccountingEntryStatus,
)

ZERO = Decimal("0.00")
# Tolerancia cero: la ecuación contable debe cuadrar exacto.
TOLERANCE = Decimal("0.00")


@dataclass(frozen=True)
class AccountBalance:
    """Saldo natural de una cuenta (derivado, no persistido)."""

    code: str
    name: str
    balance: Decimal


def _round(value: Decimal) -> Decimal:
    return value.quantize(ZERO)


def _account_balances(
    db: Session,
    *,
    from_date: date | None = None,
    to_date: date | None = None,
    before: date | None = None,
) -> dict[str, Decimal]:
    """Saldos (débito - crédito) por código con asientos POSTED del rango.

    ``before`` usa corte exclusivo (``entry_date < before``): sirve para
    el saldo de apertura del flujo de efectivo.
    """
    line_query = (
        select(
            AccountingEntryLine.account_code,
            func.coalesce(func.sum(AccountingEntryLine.debit), ZERO).label("debit"),
            func.coalesce(func.sum(AccountingEntryLine.credit), ZERO).label("credit"),
        )
        .join(AccountingEntry, AccountingEntry.id == AccountingEntryLine.entry_id)
        .where(AccountingEntry.status == AccountingEntryStatus.POSTED)
        .group_by(AccountingEntryLine.account_code)
    )
    if from_date is not None:
        line_query = line_query.where(AccountingEntry.entry_date >= from_date)
    if to_date is not None:
        line_query = line_query.where(AccountingEntry.entry_date <= to_date)
    if before is not None:
        line_query = line_query.where(AccountingEntry.entry_date < before)
    rows = db.execute(line_query).all()
    return {
        row.account_code: Decimal(str(row.debit)) - Decimal(str(row.credit)) for row in rows
    }  # saldo en términos débito - crédito


def _codes(balance_by_code: dict[str, Decimal], *prefixes: str) -> Decimal:
    """Suma el saldo débito-credito de los códigos que empiezan por los prefijos."""
    return _round(
        sum(
            (balance for code, balance in balance_by_code.items() if code.startswith(prefixes)),
            ZERO,
        )
    )


def _credit(balance: Decimal) -> Decimal:
    """Presenta un saldo naturaleza crédito como positivo."""
    return _round(-balance)


class NiifReportsService:
    """Estados financieros NIIF sobre el PUC colombiano."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def _names(self) -> dict[str, str]:
        return dict(self.db.execute(select(AccountingAccount.code, AccountingAccount.name)).all())

    @staticmethod
    def _account_rows(
        balances: dict[str, Decimal],
        names: dict[str, str],
        *prefixes: str,
        credit_side: bool,
    ) -> list[dict[str, object]]:
        """Convierte saldos débito/crédito en filas presentables por cuenta."""
        rows: list[dict[str, object]] = []
        for code in sorted(balances):
            if not code.startswith(prefixes):
                continue
            value = _credit(balances[code]) if credit_side else _round(balances[code])
            if value == ZERO:
                continue
            rows.append(
                {
                    "code": code,
                    "name": names.get(code, code),
                    "balance": value,
                }
            )
        return rows

    # -- 39C.1.1 Estado de Resultados --------------------------------------

    def income_statement_niif(
        self,
        *,
        from_date: date,
        to_date: date,
    ) -> dict[str, Any]:
        """Estado de Resultados NIIF por función (secciones PUC 4/5/6)."""
        balances = _account_balances(self.db, from_date=from_date, to_date=to_date)
        names = self._names()

        def group(*prefixes: str, credit_side: bool = True) -> list[AccountBalance]:
            rows = [
                AccountBalance(
                    code,
                    names.get(code, code),
                    _credit(balances[code]) if credit_side else balances[code],
                )
                for code in sorted(balances)
                if code.startswith(prefixes)
            ]
            return [row for row in rows if row.balance != ZERO]

        def total(*prefixes: str, credit_side: bool = True) -> Decimal:
            return _round(
                sum(
                    (row.balance for row in group(*prefixes, credit_side=credit_side)),
                    ZERO,
                )
            )

        revenue = total("4") - total("42", "43")  # 41 ordinarios, sin otros/financieros
        cost_of_sales = total("61", credit_side=False)
        gross_profit = revenue - cost_of_sales
        admin_expenses = total("51", credit_side=False)
        other_income = total("42")
        other_expenses = total("52", credit_side=False)
        financial_income = total("4305")
        financial_expenses = total("5305", credit_side=False)
        income_tax = total("5405", credit_side=False)
        operating_result = gross_profit - admin_expenses
        pretax_income = (
            operating_result + other_income - other_expenses + financial_income - financial_expenses
        )
        net_income = pretax_income - income_tax
        total_expenses = _round(
            cost_of_sales + admin_expenses + other_expenses + financial_expenses + income_tax
        )

        return {
            "from_date": from_date,
            "to_date": to_date,
            "sections": [
                {
                    "label": "Ingresos de actividades ordinarias",
                    "accounts": [group("41")],
                    "total": revenue,
                },
                {
                    "label": "Costo de ventas",
                    "accounts": [group("61", credit_side=False)],
                    "total": cost_of_sales,
                },
                {
                    "label": "Ganancia bruta",
                    "accounts": [],
                    "total": gross_profit,
                    "kind": "subtotal",
                },
                {
                    "label": "Gastos de administración y distribución",
                    "accounts": [group("51", credit_side=False)],
                    "total": admin_expenses,
                },
                {
                    "label": "Otros ingresos",
                    "accounts": [group("42")],
                    "total": other_income,
                },
                {
                    "label": "Otros gastos",
                    "accounts": [group("52", credit_side=False)],
                    "total": other_expenses,
                },
                {
                    "label": "Ingresos financieros",
                    "accounts": [group("4305")],
                    "total": financial_income,
                },
                {
                    "label": "Costos financieros",
                    "accounts": [group("5305", credit_side=False)],
                    "total": financial_expenses,
                },
                {
                    "label": "Ganancia antes de impuestos",
                    "accounts": [],
                    "total": pretax_income,
                    "kind": "subtotal",
                },
                {
                    "label": "Impuesto de renta",
                    "accounts": [group("5405", credit_side=False)],
                    "total": income_tax,
                },
                {
                    "label": "Ganancia neta del ejercicio",
                    "accounts": [],
                    "total": net_income,
                    "kind": "net",
                },
            ],
            "revenue": revenue,
            "cost_of_sales": cost_of_sales,
            "gross_profit": gross_profit,
            "total_expenses": total_expenses,
            "pretax_income": pretax_income,
            "income_tax": income_tax,
            "net_income": net_income,
        }

    # -- 39C.1.2 Balance General ---------------------------------------------

    def balance_sheet_niif(self, *, as_of_date: date) -> dict[str, Any]:
        """Balance General NIIF: corriente / no corriente + patrimonio."""
        balances = _account_balances(self.db, to_date=as_of_date)

        def debit(*prefixes: str) -> Decimal:
            return _codes(balances, *prefixes)

        def credit(*prefixes: str) -> Decimal:
            return _credit(_codes(balances, *prefixes))

        # Activos: PUC 1. Efectivo 11, CxC clientes 13, inventarios 14,
        # gastos anticipados 17. PP&E neto 15 (menos depreciación acumulada
        # 1599 que ya viene como saldo crédito), intangibles 16.
        current_assets = debit("11", "13", "14", "17")
        non_current_assets = debit("15", "16")
        total_assets = _round(current_assets + non_current_assets)

        # Pasivos: PUC 2. Proveedores 22, impuestos por pagar 24,
        # obligaciones laborales 25, CxP varias 23/26/28.
        current_liabilities = credit("22", "23", "24", "25", "26", "28")
        non_current_liabilities = credit("27")  # obligaciones financieras LP
        total_liabilities = _round(current_liabilities + non_current_liabilities)

        # Patrimonio: cuentas PUC clase 3 + Resultado del ejercicio
        # (ingresos menos costos y gastos del periodo, aún sin cerrar).
        net_income = _round(credit("4") - debit("5", "6"))
        equity = credit("3")
        total_equity = _round(equity + net_income)

        difference = _round(total_assets - total_liabilities - total_equity)
        if abs(difference) > TOLERANCE:
            raise TreasuryError(
                f"El balance no cuadra: Activo {total_assets} != "
                f"Pasivo {total_liabilities} + Patrimonio {total_equity} "
                f"(descuadre {difference})"
            )

        names = self._names()
        return {
            "as_of_date": as_of_date,
            "current_assets": current_assets,
            "non_current_assets": non_current_assets,
            "total_assets": total_assets,
            "current_liabilities": current_liabilities,
            "non_current_liabilities": non_current_liabilities,
            "total_liabilities": total_liabilities,
            "equity": equity,
            "period_result": net_income,
            "total_equity": total_equity,
            "difference": difference,
            "asset_accounts": self._account_rows(balances, names, "1", credit_side=False),
            "liability_accounts": self._account_rows(balances, names, "2", credit_side=True),
            "equity_accounts": self._account_rows(balances, names, "3", credit_side=True),
            "asset_composition": {
                "cash": debit("11"),
                "receivables": debit("13"),
                "inventory": debit("14"),
                "other_current": debit("17"),
                "non_current": non_current_assets,
            },
            "liability_equity_composition": {
                "current_liabilities": current_liabilities,
                "non_current_liabilities": non_current_liabilities,
                "equity": total_equity,
            },
        }

    # -- 39C.1.3 Flujo de Efectivo (método indirecto) --------------------------

    def cash_flow_niif(
        self,
        *,
        from_date: date,
        to_date: date,
    ) -> dict[str, Any]:
        """Flujo de Efectivo por método indirecto.

        Utilidad neta del periodo + depreciación +/- variación del capital
        de trabajo (saldos de cierre menos saldos de apertura), inversión
        en PP&E e intangibles y flujos de financiación del patrimonio.
        El efectivo de cierre debe coincidir con el saldo PUC 11.
        """
        period = _account_balances(self.db, from_date=from_date, to_date=to_date)
        opening = _account_balances(self.db, before=from_date)
        closing = _account_balances(self.db, to_date=to_date)

        def debit(balances: dict[str, Decimal], *prefixes: str) -> Decimal:
            return _codes(balances, *prefixes)

        def credit(balances: dict[str, Decimal], *prefixes: str) -> Decimal:
            return _credit(_codes(balances, *prefixes))

        def variation(*prefixes: str) -> Decimal:
            return _round(_codes(closing, *prefixes) - _codes(opening, *prefixes))

        revenues = credit(period, "41")
        costs = debit(period, "61")
        expenses = debit(period, "5")
        net_income = _round(revenues - costs - expenses)
        depreciation = debit(period, "5160")

        receivables_change = variation("13")
        inventory_change = variation("14")
        payables_change = _round(
            -(
                _codes(closing, "22", "23", "25", "26", "28")
                - _codes(opening, "22", "23", "25", "26", "28")
            )
        )

        operating = _round(
            net_income + depreciation - receivables_change - inventory_change + payables_change
        )
        investing = _round(-debit(period, "15", "16"))
        financing = _round(credit(period, "31", "32", "33", "34", "36"))

        net_change = _round(operating + investing + financing)
        opening_cash = debit(opening, "11")
        closing_cash = _round(opening_cash + net_change)
        real_closing_cash = debit(closing, "11")

        return {
            "from_date": from_date,
            "to_date": to_date,
            "net_income": net_income,
            "depreciation": depreciation,
            "receivables_change": receivables_change,
            "inventory_change": inventory_change,
            "payables_change": payables_change,
            "operating_cash_flow": operating,
            "investing_cash_flow": investing,
            "financing_cash_flow": financing,
            "net_cash_change": net_change,
            "opening_cash": opening_cash,
            "closing_cash": closing_cash,
            "bank_closing_cash": real_closing_cash,
        }


__all__ = ["NiifReportsService"]
