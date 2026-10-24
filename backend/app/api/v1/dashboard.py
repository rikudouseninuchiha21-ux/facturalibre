"""Endpoint de métricas agregadas para el panel de control."""

from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.dependencies.auth import get_current_user
from app.application.dashboard_schemas import (
    DashboardSummary,
    InvoiceStatusSummary,
    MonthlySalesSummary,
)
from app.domain.calculations import ZERO_MONEY
from app.domain.dashboard_repository import DashboardRepository
from app.domain.models.invoice import LifecycleStatus
from app.infrastructure.database import get_db

router = APIRouter(
    prefix="/dashboard",
    tags=["dashboard"],
    dependencies=[Depends(get_current_user)],
)

DbSession = Annotated[Session, Depends(get_db)]

MONTHS_IN_DASHBOARD = 6


def get_dashboard_repository(db: DbSession) -> DashboardRepository:
    """Construye el repositorio de métricas con la sesión de la petición."""
    return DashboardRepository(db)


DashboardRepositoryDep = Annotated[
    DashboardRepository,
    Depends(get_dashboard_repository),
]


def _shift_month(year: int, month: int, offset: int) -> tuple[int, int]:
    """Desplaza un mes de calendario preservando el año."""
    month_index = (year * 12) + (month - 1) + offset
    return month_index // 12, (month_index % 12) + 1


@router.get("/summary", response_model=DashboardSummary)
def get_dashboard_summary(
    repository: DashboardRepositoryDep,
) -> DashboardSummary:
    """Devuelve KPIs, distribución de facturas y ventas de los últimos 6 meses."""
    today = date.today()
    start_year, start_month = _shift_month(
        today.year,
        today.month,
        -(MONTHS_IN_DASHBOARD - 1),
    )
    end_year, end_month = _shift_month(today.year, today.month, 1)

    snapshot = repository.get_snapshot(
        start_date=date(start_year, start_month, 1),
        end_date=date(end_year, end_month, 1),
    )

    totals_by_month = {(row.year, row.month): row.total for row in snapshot.monthly_sales}
    monthly_sales: list[MonthlySalesSummary] = []
    for offset in range(-(MONTHS_IN_DASHBOARD - 1), 1):
        year, month = _shift_month(today.year, today.month, offset)
        monthly_sales.append(
            MonthlySalesSummary(
                month=f"{year:04d}-{month:02d}",
                total=totals_by_month.get((year, month), ZERO_MONEY),
            )
        )

    counts = snapshot.invoices_by_status
    return DashboardSummary(
        total_revenue=snapshot.total_revenue,
        total_invoiced=snapshot.total_invoiced,
        pending_balance=snapshot.pending_balance,
        invoices_by_status=InvoiceStatusSummary(
            draft=counts.get(LifecycleStatus.DRAFT, 0),
            issued=counts.get(LifecycleStatus.ISSUED, 0),
            void=counts.get(LifecycleStatus.VOID, 0),
        ),
        monthly_sales=monthly_sales,
    )
