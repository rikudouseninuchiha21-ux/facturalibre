"""Reporte Presupuesto vs Real por centro de costo.

El gasto "real" se deriva exclusivamente de la contabilidad
(``accounting_entry_lines`` etiquetadas con centro de costo) para mantener
una sola fuente de verdad; no existe una tabla paralela de gastos.

Todos los cálculos usan ``Decimal``; no hay ningún ``float``.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy.orm import Session

from app.application.budget_schemas import (
    BudgetVsActualLine,
    BudgetVsActualReportResponse,
    BudgetVsActualResponse,
    BudgetVsActualTotals,
)
from app.application.cost_center_schemas import CostCenterRead
from app.domain.budget_repository import BudgetRepository
from app.domain.calculations import round_money
from app.domain.exceptions import ResourceNotFoundError
from app.domain.models.budgeting import Budget

ZERO = Decimal("0.00")
HUNDRED = Decimal("100")


def _variance_pct(variance: Decimal, budgeted: Decimal) -> Decimal | None:
    """Porcentaje de desviación; None cuando no hay base presupuestada."""
    if budgeted == ZERO:
        return None
    return round_money(variance / budgeted * HUNDRED)


def _month_window(period_year: int, period_month: int) -> tuple[date, date]:
    """Devuelve [primer día del mes, primer día del mes siguiente)."""
    start = date(period_year, period_month, 1)
    if period_month == 12:
        return start, date(period_year + 1, 1, 1)
    return start, date(period_year, period_month + 1, 1)


class BudgetActualsService:
    """Compara lo presupuestado contra el gasto real del mes."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.budgets = BudgetRepository(db)

    def report(self, budget_id: UUID) -> BudgetVsActualResponse:
        """Genera el bloque Presupuesto vs Real de un presupuesto concreto."""
        budget = self.budgets.get_by_id(budget_id)
        if budget is None:
            raise ResourceNotFoundError("Presupuesto no encontrado")
        return self._build_report(budget)

    def report_by_period(
        self,
        *,
        period_year: int,
        period_month: int,
        cost_center_id: UUID | None = None,
    ) -> BudgetVsActualReportResponse:
        """Agrega un bloque por presupuesto que matchea el periodo (y centro)."""
        budgets = self.budgets.list(
            cost_center_id=cost_center_id,
            period_year=period_year,
            period_month=period_month,
            limit=100,
            offset=0,
        )
        blocks = [self._build_report(budget) for budget in budgets]
        return BudgetVsActualReportResponse(
            period_year=period_year,
            period_month=period_month,
            cost_center_id=cost_center_id,
            blocks=blocks,
        )

    def _build_report(self, budget: Budget) -> BudgetVsActualResponse:
        start, end = _month_window(budget.period_year, budget.period_month)
        account_codes = [line.account_code for line in budget.lines]
        actual_by_account = self.budgets.sum_actual_by_account(
            cost_center_id=budget.cost_center_id,
            account_codes=account_codes,
            start_date=start,
            end_date=end,
        )

        lines: list[BudgetVsActualLine] = []
        total_budgeted = ZERO
        total_actual = ZERO
        for line in budget.lines:
            budgeted = round_money(Decimal(str(line.amount)))
            actual = round_money(actual_by_account.get(line.account_code, ZERO))
            variance = round_money(actual - budgeted)
            total_budgeted = round_money(total_budgeted + budgeted)
            total_actual = round_money(total_actual + actual)
            lines.append(
                BudgetVsActualLine(
                    account_code=line.account_code,
                    account_name=(
                        line.account.name if line.account is not None else line.account_code
                    ),
                    budgeted=budgeted,
                    actual=actual,
                    variance=variance,
                    variance_pct=_variance_pct(variance, budgeted),
                )
            )

        total_variance = round_money(total_actual - total_budgeted)
        return BudgetVsActualResponse(
            budget_id=budget.id,
            cost_center=CostCenterRead.model_validate(budget.cost_center),
            period_year=budget.period_year,
            period_month=budget.period_month,
            status=budget.status.value,
            lines=lines,
            totals=BudgetVsActualTotals(
                budgeted=total_budgeted,
                actual=total_actual,
                variance=total_variance,
                variance_pct=_variance_pct(total_variance, total_budgeted),
            ),
        )


__all__ = ["BudgetActualsService"]
