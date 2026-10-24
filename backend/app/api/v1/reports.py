"""Endpoints de exportación de reportes a CSV y estados financieros."""

from __future__ import annotations

import csv
import io
from collections.abc import Iterable
from datetime import date
from decimal import Decimal
from typing import Annotated, Any, cast

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.dependencies.auth import get_current_user, require_role
from app.application.report_schemas import (
    AccountReportRow,
    BalanceSheetResponse,
    IncomeStatementResponse,
)
from app.domain.accounting_repository import AccountingRepository
from app.domain.models.accounting import (
    AccountingAccount,
    AccountingEntry,
    AccountingEntryLine,
    AccountingEntryStatus,
)
from app.domain.models.auth import UserRole
from app.domain.models.invoice import LifecycleStatus
from app.domain.reports_repository import (
    InvoiceExportRow,
    PaymentExportRow,
    ReportsRepository,
)
from app.infrastructure.database import get_db

router = APIRouter(
    prefix="/reports",
    tags=["reports"],
    dependencies=[
        Depends(get_current_user),
        Depends(require_role([UserRole.ACCOUNTANT, UserRole.ADMIN])),
    ],
)

DbSession = Annotated[Session, Depends(get_db)]

INVOICE_CSV_FILENAME = "facturas.csv"
PAYMENT_CSV_FILENAME = "pagos.csv"

INVOICE_STATUS_LABELS: dict[LifecycleStatus, str] = {
    LifecycleStatus.DRAFT: "Borrador",
    LifecycleStatus.ISSUED: "Emitida",
    LifecycleStatus.VOID: "Anulada",
}


def get_reports_repository(db: DbSession) -> ReportsRepository:
    """Construye el repositorio de reportes con la sesión de la petición."""
    return ReportsRepository(db)


ReportsRepositoryDep = Annotated[
    ReportsRepository,
    Depends(get_reports_repository),
]


def get_accounting_repository(db: DbSession) -> AccountingRepository:
    """Construye el repositorio contable con la sesión de la petición."""
    return AccountingRepository(db)


AccountingRepositoryDep = Annotated[
    AccountingRepository,
    Depends(get_accounting_repository),
]


def _parse_date(value: str | None) -> date | None:
    if value is None:
        return None
    return date.fromisoformat(value)


def _format_money(value: Decimal) -> str:
    """Formatea un importe decimal con dos decimales para los reportes."""
    return f"{value:.2f}"


@router.get("/income-statement", response_model=IncomeStatementResponse)
def get_income_statement(
    repository: AccountingRepositoryDep,
    start_date: Annotated[str | None, Query()] = None,
    end_date: Annotated[str | None, Query()] = None,
) -> IncomeStatementResponse:
    """Estado de Resultados: ingresos, gastos y utilidad neta en un rango."""
    start = _parse_date(start_date)
    end = _parse_date(end_date)

    # Para el estado de resultados usamos el rango de fechas del asiento.
    # Calculamos saldos de cuentas INGRESO y GASTO entre start_date y end_date.
    line_subquery = (
        select(
            AccountingEntryLine.account_code,
            func.coalesce(func.sum(AccountingEntryLine.debit), 0).label("total_debit"),
            func.coalesce(func.sum(AccountingEntryLine.credit), 0).label("total_credit"),
        )
        .join(
            AccountingEntry,
            AccountingEntry.id == AccountingEntryLine.entry_id,
        )
        .where(AccountingEntry.status == AccountingEntryStatus.POSTED)
    )
    if start is not None:
        line_subquery = line_subquery.where(AccountingEntry.entry_date >= start)
    if end is not None:
        line_subquery = line_subquery.where(AccountingEntry.entry_date <= end)
    line_subquery = cast(
        Any,
        line_subquery.group_by(AccountingEntryLine.account_code).subquery(),
    )

    statement = (
        select(
            AccountingAccount.code,
            AccountingAccount.name,
            AccountingAccount.account_type,
            AccountingAccount.nature,
            func.coalesce(line_subquery.c.total_debit, 0).label("total_debit"),
            func.coalesce(line_subquery.c.total_credit, 0).label("total_credit"),
        )
        .outerjoin(
            line_subquery,
            line_subquery.c.account_code == AccountingAccount.code,
        )
        .where(AccountingAccount.account_type.in_(["INGRESO", "GASTO"]))
        .order_by(AccountingAccount.code)
    )

    rows = repository.db.execute(statement).all()

    income_accounts: list[AccountReportRow] = []
    expense_accounts: list[AccountReportRow] = []
    total_income = Decimal("0.00")
    total_expenses = Decimal("0.00")

    for row in rows:
        total_debit = Decimal(str(row.total_debit))
        total_credit = Decimal(str(row.total_credit))
        if row.nature == "DEBITO":
            balance = total_debit - total_credit
        else:
            balance = total_credit - total_debit

        row_data = AccountReportRow(
            code=row.code,
            name=row.name,
            balance=_format_money(balance),
        )

        if row.account_type == "INGRESO":
            income_accounts.append(row_data)
            total_income += balance
        elif row.account_type == "GASTO":
            expense_accounts.append(row_data)
            total_expenses += balance

    net_income = total_income - total_expenses

    return IncomeStatementResponse(
        income_accounts=income_accounts,
        expense_accounts=expense_accounts,
        total_income=_format_money(total_income),
        total_expenses=_format_money(total_expenses),
        net_income=_format_money(net_income),
    )


@router.get("/balance-sheet", response_model=BalanceSheetResponse)
def get_balance_sheet(
    repository: AccountingRepositoryDep,
    as_of_date: Annotated[str | None, Query()] = None,
) -> BalanceSheetResponse:
    """Balance General: activos, pasivos, patrimonio a una fecha de corte."""
    cutoff = _parse_date(as_of_date)

    balances = repository.get_account_balances(as_of_date=cutoff)

    asset_accounts: list[AccountReportRow] = []
    liability_accounts: list[AccountReportRow] = []
    equity_accounts: list[AccountReportRow] = []
    total_assets = Decimal("0.00")
    total_liabilities = Decimal("0.00")
    total_equity = Decimal("0.00")

    for b in balances:
        balance = b["balance"]
        row_data = AccountReportRow(
            code=b["code"],
            name=b["name"],
            balance=_format_money(balance),
        )
        if b["account_type"] == "ACTIVO":
            asset_accounts.append(row_data)
            total_assets += balance
        elif b["account_type"] == "PASIVO":
            liability_accounts.append(row_data)
            total_liabilities += balance
        elif b["account_type"] == "PATRIMONIO":
            equity_accounts.append(row_data)
            total_equity += balance

    # El resultado del ejercicio (Ingresos - Gastos) se incorpora al patrimonio
    # para que el balance cuadre: Activo = Pasivo + Patrimonio + Resultado
    income_stmt = get_income_statement(
        repository,
        start_date=None,
        end_date=cutoff.isoformat() if cutoff else None,
    )
    net_income = Decimal(income_stmt.net_income)
    total_equity += net_income

    balanced = total_assets == (total_liabilities + total_equity)

    return BalanceSheetResponse(
        asset_accounts=asset_accounts,
        liability_accounts=liability_accounts,
        equity_accounts=equity_accounts,
        total_assets=_format_money(total_assets),
        total_liabilities=_format_money(total_liabilities),
        total_equity=_format_money(total_equity),
        balanced=balanced,
    )


def _csv_stream(fieldnames: list[str], rows: Iterable[dict[str, str]]) -> Iterable[bytes]:
    """Genera el CSV codificado en utf-8-sig (BOM incluido para Excel)."""
    # El BOM de UTF-8 permite que Excel en Windows detecte la codificación.
    yield "\ufeff".encode("utf-8")

    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=fieldnames, lineterminator="\n")
    writer.writeheader()
    yield buffer.getvalue().encode("utf-8")
    buffer.seek(0)
    buffer.truncate(0)

    for row in rows:
        writer.writerow(row)
        yield buffer.getvalue().encode("utf-8")
        buffer.seek(0)
        buffer.truncate(0)


def _invoices_rows(
    invoices: list[InvoiceExportRow],
) -> Iterable[dict[str, str]]:
    for invoice in invoices:
        yield {
            "Número": invoice.number or "—",
            "Fecha Emisión": (invoice.issue_date.isoformat() if invoice.issue_date else ""),
            "Cliente": invoice.contact_name,
            "Subtotal": _format_money(invoice.subtotal),
            "Impuestos": _format_money(invoice.tax_total),
            "Total": _format_money(invoice.total),
            "Estado": INVOICE_STATUS_LABELS[invoice.lifecycle_status],
        }


def _payments_rows(
    payments: list[PaymentExportRow],
) -> Iterable[dict[str, str]]:
    for payment in payments:
        yield {
            "Factura": payment.invoice_number or "—",
            "Fecha Pago": payment.payment_date.isoformat(),
            "Monto": _format_money(payment.amount),
            "Método": payment.method,
        }


@router.get("/invoices.csv")
def export_invoices_csv(
    repository: ReportsRepositoryDep,
) -> StreamingResponse:
    """Exporta las facturas no eliminadas a un archivo CSV."""
    fieldnames = [
        "Número",
        "Fecha Emisión",
        "Cliente",
        "Subtotal",
        "Impuestos",
        "Total",
        "Estado",
    ]
    return StreamingResponse(
        _csv_stream(
            fieldnames,
            _invoices_rows(repository.list_invoices_for_export()),
        ),
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="{INVOICE_CSV_FILENAME}"',
        },
    )


@router.get("/payments.csv")
def export_payments_csv(
    repository: ReportsRepositoryDep,
) -> StreamingResponse:
    """Exporta los pagos recibidos a un archivo CSV."""
    fieldnames = ["Factura", "Fecha Pago", "Monto", "Método"]
    return StreamingResponse(
        _csv_stream(
            fieldnames,
            _payments_rows(repository.list_payments_for_export()),
        ),
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="{PAYMENT_CSV_FILENAME}"',
        },
    )
