"""Schemas de respuesta del panel de control."""

from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel


class InvoiceStatusSummary(BaseModel):
    """Conteo de facturas por estado de ciclo de vida."""

    draft: int
    issued: int
    void: int


class MonthlySalesSummary(BaseModel):
    """Total facturado en un mes."""

    month: str
    total: Decimal


class DashboardSummary(BaseModel):
    """Métricas principales del dashboard."""

    total_revenue: Decimal
    total_invoiced: Decimal
    pending_balance: Decimal
    invoices_by_status: InvoiceStatusSummary
    monthly_sales: list[MonthlySalesSummary]
