"""Cierre de periodos contables mensuales."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.domain.accounting_repository import FiscalPeriodRepository
from app.domain.models.accounting import FiscalPeriod, FiscalPeriodStatus


class FiscalPeriodError(Exception):
    """El periodo no puede cerrarse por su estado o por inconsistencias."""


class FiscalPeriodService:
    """Coordina la validación y el cierre de un mes contable."""

    def __init__(self, db: Session) -> None:
        self.repository = FiscalPeriodRepository(db)

    def close_period(self, *, year: int, month: int) -> FiscalPeriod:
        """Cierra un periodo después de validar que todos sus asientos cuadran.

        No hace commit: la API envuelve la operación con
        ``operation_transaction`` para que la validación y el cambio de estado
        sean atómicos.
        """
        period = self.repository.get_period(year=year, month=month)
        if period is not None and period.status == FiscalPeriodStatus.CLOSED:
            raise FiscalPeriodError(
                f"El periodo contable {month:02d}/{year} ya está cerrado"
            )

        unbalanced = self.repository.list_unbalanced_entry_ids(year=year, month=month)
        if unbalanced:
            identifiers = ", ".join(str(entry_id) for entry_id in unbalanced)
            raise FiscalPeriodError(
                "No se puede cerrar el periodo: hay asientos descuadrados "
                f"({identifiers})"
            )

        closed_at = datetime.now(UTC)
        if period is None:
            period = FiscalPeriod(
                year=year,
                month=month,
                status=FiscalPeriodStatus.CLOSED,
                closed_at=closed_at,
            )
            return self.repository.add_period(period)

        period.status = FiscalPeriodStatus.CLOSED
        period.closed_at = closed_at
        self.repository.db.flush()
        return period
