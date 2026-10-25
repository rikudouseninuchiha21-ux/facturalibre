"""Repositorio de presupuestos mensuales y sus líneas.

El repositorio nunca confirma transacciones; la capa de API agrupa las
operaciones con ``operation_transaction``.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.domain.models.accounting import (
    AccountingEntry,
    AccountingEntryLine,
    AccountingEntryStatus,
)
from app.domain.models.budgeting import Budget, BudgetLine, BudgetStatus, CostCenter


class BudgetRepository:
    """Acceso a datos de presupuestos y líneas presupuestales."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, values: dict[str, Any]) -> Budget:
        """Crea un presupuesto DRAFT sin confirmar la transacción."""
        budget = Budget(**values)
        self.db.add(budget)
        self.db.flush()
        self.db.refresh(budget)
        return budget

    def get_by_id(self, budget_id: UUID) -> Budget | None:
        return self.db.scalar(
            select(Budget)
            .where(Budget.id == budget_id)
            .options(
                selectinload(Budget.lines).selectinload(BudgetLine.account),
                selectinload(Budget.cost_center),
            )
        )

    def find_by_period(
        self,
        *,
        cost_center_id: UUID,
        period_year: int,
        period_month: int,
    ) -> Budget | None:
        """Devuelve el presupuesto único de un centro para un mes, si existe."""
        return self.db.scalar(
            select(Budget).where(
                Budget.cost_center_id == cost_center_id,
                Budget.period_year == period_year,
                Budget.period_month == period_month,
            )
        )

    def list(
        self,
        *,
        cost_center_id: UUID | None = None,
        period_year: int | None = None,
        period_month: int | None = None,
        status: BudgetStatus | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Budget]:
        statement = (
            select(Budget)
            .options(
                selectinload(Budget.lines),
                selectinload(Budget.cost_center),
            )
            .order_by(Budget.period_year.desc(), Budget.period_month.desc(), Budget.id)
        )
        if cost_center_id is not None:
            statement = statement.where(Budget.cost_center_id == cost_center_id)
        if period_year is not None:
            statement = statement.where(Budget.period_year == period_year)
        if period_month is not None:
            statement = statement.where(Budget.period_month == period_month)
        if status is not None:
            statement = statement.where(Budget.status == status)
        statement = statement.limit(limit).offset(offset)
        return list(self.db.scalars(statement).all())

    def update(self, budget: Budget, values: dict[str, Any]) -> Budget:
        for field, value in values.items():
            setattr(budget, field, value)
        self.db.flush()
        self.db.refresh(budget)
        return budget

    def delete(self, budget: Budget) -> None:
        self.db.delete(budget)
        self.db.flush()

    # -- Líneas ---------------------------------------------------------

    def line_exists(self, budget_id: UUID, account_code: str) -> bool:
        return (
            self.db.scalar(
                select(BudgetLine.id).where(
                    BudgetLine.budget_id == budget_id,
                    BudgetLine.account_code == account_code,
                )
            )
            is not None
        )

    def get_line(self, budget_id: UUID, line_id: UUID) -> BudgetLine | None:
        return self.db.scalar(
            select(BudgetLine).where(
                BudgetLine.budget_id == budget_id,
                BudgetLine.id == line_id,
            )
        )

    def add_line(
        self,
        budget: Budget,
        *,
        account_code: str,
        amount: Decimal,
        notes: str | None,
    ) -> BudgetLine:
        line = BudgetLine(account_code=account_code, amount=amount, notes=notes)
        # Se agrega a la colección para que el identity map y la relación
        # queden consistentes sin depender de expire/refresh.
        budget.lines.append(line)
        self.db.flush()
        self.db.refresh(line)
        return line

    def update_line(self, line: BudgetLine, values: dict[str, Any]) -> BudgetLine:
        for field, value in values.items():
            setattr(line, field, value)
        self.db.flush()
        self.db.refresh(line)
        return line

    def remove_line(self, line: BudgetLine) -> None:
        """Quita la línea del presupuesto.

        Se elimina desde la colección para que el cascade ``delete-orphan``
        borre la fila y el estado en memoria (identity map) quede consistente;
        ``Session.delete`` directo no actualiza la colección ya cargada.
        """
        line.budget.lines.remove(line)
        self.db.flush()

    # -- Real (derivado de la contabilidad) ------------------------------

    def sum_actual_by_account(
        self,
        *,
        cost_center_id: UUID,
        account_codes: Sequence[str],
        start_date: date,
        end_date: date,
    ) -> dict[str, Decimal]:
        """Agrega el gasto real por cuenta dentro de un rango de fechas.

        El "real" es el saldo natural de las líneas contables etiquetadas con
        el centro de costo: ``SUM(debit - credit)`` de asientos POSTED. Solo
        se consultan las cuentas presupuestadas.
        """
        if not account_codes:
            return {}

        rows = self.db.execute(
            select(
                AccountingEntryLine.account_code,
                AccountingEntryLine.debit - AccountingEntryLine.credit,
            )
            .join(AccountingEntry, AccountingEntry.id == AccountingEntryLine.entry_id)
            .where(
                AccountingEntry.status == AccountingEntryStatus.POSTED,
                AccountingEntry.entry_date >= start_date,
                AccountingEntry.entry_date < end_date,
                AccountingEntryLine.cost_center_id == cost_center_id,
                AccountingEntryLine.account_code.in_(account_codes),
            )
        ).all()

        totals: dict[str, Decimal] = {}
        for code, movement in rows:
            value = Decimal(str(movement))
            totals[code] = totals.get(code, Decimal("0.00")) + value
        return totals

    def cost_center_by_id(self, cost_center_id: UUID) -> CostCenter | None:
        return self.db.scalar(select(CostCenter).where(CostCenter.id == cost_center_id))


__all__ = ["BudgetRepository"]
