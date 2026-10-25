"""Cierre de periodos contables mensuales."""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.application.budget_service import BudgetService
from app.domain.accounting_repository import FiscalPeriodRepository
from app.domain.models.accounting import FiscalPeriod, FiscalPeriodStatus

logger = logging.getLogger(__name__)


class FiscalPeriodError(Exception):
    """El periodo no puede cerrarse por su estado o por inconsistencias."""


class FiscalPeriodService:
    """Coordina la validación y el cierre de un mes contable."""

    def __init__(self, db: Session) -> None:
        self.repository = FiscalPeriodRepository(db)

    def close_period(self, *, year: int, month: int) -> FiscalPeriod:
        """Cierra un periodo después de validar que todos sus asientos cuadran.

        En la misma transacción cierra automáticamente los presupuestos
        APPROVED del mes (ver ``BudgetService.close_by_period``): si el
        cierre del periodo falla, ningún presupuesto queda a medio cerrar.

        No hace commit: la API envuelve la operación con
        ``operation_transaction`` para que la validación, el cambio de
        estado y el cierre presupuestal sean atómicos.
        """
        period = self.repository.get_period(year=year, month=month)
        if period is not None and period.status == FiscalPeriodStatus.CLOSED:
            raise FiscalPeriodError(f"El periodo contable {month:02d}/{year} ya está cerrado")

        unbalanced = self.repository.list_unbalanced_entry_ids(year=year, month=month)
        if unbalanced:
            identifiers = ", ".join(str(entry_id) for entry_id in unbalanced)
            raise FiscalPeriodError(
                f"No se puede cerrar el periodo: hay asientos descuadrados ({identifiers})"
            )

        closed_at = datetime.now(UTC)
        if period is None:
            period = self.repository.add_period(
                FiscalPeriod(
                    year=year,
                    month=month,
                    status=FiscalPeriodStatus.CLOSED,
                    closed_at=closed_at,
                )
            )
        else:
            period.status = FiscalPeriodStatus.CLOSED
            period.closed_at = closed_at
            self.repository.db.flush()

        # Cierre presupuestal automático dentro de la misma transacción.
        # La reapertura del periodo NO reabre presupuestos (decisión manual).
        auto_closed = BudgetService(self.repository.db).close_by_period(
            period_year=year,
            period_month=month,
        )
        logger.info("budgets_auto_closed=%d", auto_closed)
        return period
