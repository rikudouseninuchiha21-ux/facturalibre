"""Consultas agregadas para el panel de control."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.domain.calculations import ZERO_MONEY, round_money
from app.domain.models.invoice import Invoice, LifecycleStatus
from app.domain.models.payment import Payment


@dataclass(frozen=True)
class MonthlySalesRow:
    """Venta agregada de un mes concreto."""

    year: int
    month: int
    total: Decimal


@dataclass(frozen=True)
class DashboardSnapshot:
    """Métricas base del panel, antes de completar meses sin ventas."""

    total_revenue: Decimal
    total_invoiced: Decimal
    pending_balance: Decimal
    invoices_by_status: dict[LifecycleStatus, int]
    monthly_sales: list[MonthlySalesRow]


def _as_money(value: object | None) -> Decimal:
    """Normaliza agregados SQL, que pueden llegar como Decimal o None."""
    if value is None:
        return ZERO_MONEY
    if isinstance(value, Decimal):
        return round_money(value)
    return round_money(Decimal(str(value)))


class DashboardRepository:
    """Acceso a las consultas de solo lectura del dashboard."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_snapshot(self, *, start_date: date, end_date: date) -> DashboardSnapshot:
        """Calcula KPIs, conteos y ventas mensuales en el rango indicado."""
        revenue = self.db.scalar(select(func.coalesce(func.sum(Payment.amount), ZERO_MONEY)))

        issued_totals = self.db.execute(
            select(
                func.coalesce(func.sum(Invoice.total), ZERO_MONEY),
                func.coalesce(func.sum(Invoice.balance), ZERO_MONEY),
            ).where(
                Invoice.lifecycle_status == LifecycleStatus.ISSUED,
                Invoice.deleted_at.is_(None),
            )
        ).one()
        total_invoiced, pending_balance = issued_totals

        status_rows = self.db.execute(
            select(Invoice.lifecycle_status, func.count(Invoice.id))
            .where(Invoice.deleted_at.is_(None))
            .group_by(Invoice.lifecycle_status)
        ).all()
        invoices_by_status = {status: 0 for status in LifecycleStatus}
        for status, count in status_rows:
            invoices_by_status[status] = int(count)

        # extract('year') y extract('month') agrupan las ventas por periodo sin
        # depender del formato de fecha ni de la zona horaria del servidor.
        year_expression = func.extract("year", Invoice.issue_date)
        month_expression = func.extract("month", Invoice.issue_date)
        monthly_rows = self.db.execute(
            select(
                year_expression,
                month_expression,
                func.coalesce(func.sum(Invoice.total), ZERO_MONEY),
            )
            .where(
                Invoice.lifecycle_status == LifecycleStatus.ISSUED,
                Invoice.deleted_at.is_(None),
                Invoice.issue_date.is_not(None),
                Invoice.issue_date >= start_date,
                Invoice.issue_date < end_date,
            )
            .group_by(year_expression, month_expression)
            .order_by(year_expression, month_expression)
        ).all()

        monthly_sales = [
            MonthlySalesRow(
                year=int(year),
                month=int(month),
                total=_as_money(total),
            )
            for year, month, total in monthly_rows
        ]

        return DashboardSnapshot(
            total_revenue=_as_money(revenue),
            total_invoiced=_as_money(total_invoiced),
            pending_balance=_as_money(pending_balance),
            invoices_by_status=invoices_by_status,
            monthly_sales=monthly_sales,
        )
