"""Schemas Pydantic para reportes financieros y de liquidez."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class AccountReportRow(BaseModel):
    """Fila de reporte de saldo por cuenta contable."""

    model_config = ConfigDict(from_attributes=True)

    code: str
    name: str
    balance: str  # Decimal serializado como string


class IncomeStatementResponse(BaseModel):
    """Estado de Resultados: ingresos, gastos y utilidad neta."""

    income_accounts: list[AccountReportRow]
    expense_accounts: list[AccountReportRow]
    total_income: str
    total_expenses: str
    net_income: str


class BalanceSheetResponse(BaseModel):
    """Balance General: activos, pasivos, patrimonio y cuadrado."""

    asset_accounts: list[AccountReportRow]
    liability_accounts: list[AccountReportRow]
    equity_accounts: list[AccountReportRow]
    total_assets: str
    total_liabilities: str
    total_equity: str
    balanced: bool


class AgingBucketSummary(BaseModel):
    """Total y cantidad de facturas de un rango de mora."""

    key: str
    label: str
    total: Decimal
    invoice_count: int


class AgingClientRow(BaseModel):
    """Saldo pendiente de un cliente agrupado por rango de mora."""

    contact_id: UUID
    contact_name: str
    total_balance: Decimal
    max_days_overdue: int
    oldest_due_date: date | None
    invoice_count: int
    buckets: dict[str, Decimal]


class AgingReportResponse(BaseModel):
    """Reporte de cartera por antigüedad de saldos."""

    as_of: date
    total_receivable: Decimal
    buckets: list[AgingBucketSummary]
    clients: list[AgingClientRow]


class CashFlowIncomeSources(BaseModel):
    """Desglose de los ingresos reales de caja."""

    customer_payments: Decimal
    bank_deposits: Decimal


class CashFlowExpenseSources(BaseModel):
    """Desglose de los egresos reales de caja."""

    supplier_payments: Decimal
    expenses: Decimal
    bank_withdrawals: Decimal


class CashFlowMonth(BaseModel):
    """Flujo de caja real de un mes calendario."""

    month: str
    income: Decimal
    expenses: Decimal
    net: Decimal
    income_sources: CashFlowIncomeSources
    expense_sources: CashFlowExpenseSources


class CashFlowProjection(BaseModel):
    """Proyección simple de cobros con la cartera pendiente."""

    horizon_days: int
    due_within_30_days: Decimal
    overdue_balance: Decimal
    expected_collections: Decimal
    invoice_count: int


class CashFlowReportResponse(BaseModel):
    """Flujo de caja histórico y proyección de cobros."""

    as_of: date
    months: list[CashFlowMonth]
    projection: CashFlowProjection
