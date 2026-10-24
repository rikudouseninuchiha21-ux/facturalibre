"""Schemas Pydantic para reportes financieros."""

from __future__ import annotations

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
