"""Endpoints de exportación de reportes a CSV y estados financieros."""

from __future__ import annotations

import csv
import io
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal
from typing import Annotated, Any, cast
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.dependencies.auth import get_current_user, require_role
from app.application.accounting.niif_reports import NiifReportsService
from app.application.accounting.schemas import AccountingAccountRead
from app.application.budget_actuals_service import BudgetActualsService
from app.application.budget_schemas import BudgetVsActualReportResponse
from app.application.report_schemas import (
    AccountReportRow,
    AgingBucketSummary,
    AgingClientRow,
    AgingReportResponse,
    BalanceSheetPreviousPeriod,
    BalanceSheetResponse,
    CashFlowExpenseSources,
    CashFlowIncomeSources,
    CashFlowMonth,
    CashFlowProjection,
    CashFlowReportResponse,
    DrillDownMovement,
    DrillDownResponse,
    IncomeStatementPreviousPeriod,
    IncomeStatementResponse,
    LedgerMovementRead,
    LedgerReportResponse,
    TrialBalanceResponse,
    TrialBalanceRow,
)
from app.application.reports.excel_exporter import (
    export_balance_sheet_xlsx,
    export_income_statement_xlsx,
)
from app.domain.accounting_repository import AccountingRepository
from app.domain.calculations import ZERO_MONEY, round_money
from app.domain.company_setting_repository import CompanySettingRepository
from app.domain.exceptions import ResourceNotFoundError
from app.domain.models.accounting import (
    AccountingAccount,
    AccountingEntry,
    AccountingEntryLine,
    AccountingEntryStatus,
)
from app.domain.models.auth import UserRole
from app.domain.models.invoice import LifecycleStatus
from app.domain.reports_repository import (
    AgingInvoiceRow,
    InvoiceExportRow,
    MonthlyCashFlowRow,
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

AGING_BUCKETS: tuple[tuple[str, str], ...] = (
    ("0_30", "0-30 días"),
    ("31_60", "31-60 días"),
    ("61_90", "61-90 días"),
    ("over_90", "> 90 días"),
)
CASH_FLOW_MONTHS = 6
PROJECTION_HORIZON_DAYS = 30


@dataclass
class ClientAgingAccumulator:
    """Acumulador mutable para consolidar la cartera de un cliente."""

    contact_id: UUID
    contact_name: str
    total_balance: Decimal = ZERO_MONEY
    max_days_overdue: int = 0
    oldest_due_date: date | None = None
    invoice_count: int = 0
    buckets: dict[str, Decimal] = field(
        default_factory=lambda: {key: ZERO_MONEY for key, _ in AGING_BUCKETS}
    )


def _shift_month(year: int, month: int, offset: int) -> tuple[int, int]:
    """Desplaza un mes de calendario preservando el año."""
    month_index = (year * 12) + (month - 1) + offset
    return month_index // 12, (month_index % 12) + 1


def _aging_bucket(days_overdue: int) -> str:
    """Clasifica los días de mora en uno de los cuatro rangos del aging."""
    if days_overdue <= 30:
        return "0_30"
    if days_overdue <= 60:
        return "31_60"
    if days_overdue <= 90:
        return "61_90"
    return "over_90"


def _effective_due_date(row: AgingInvoiceRow, as_of: date) -> date:
    """Usa el vencimiento; si falta, cae a emisión y finalmente a la fecha de corte."""
    return row.due_date or row.issue_date or as_of


def _days_overdue(due_date: date, as_of: date) -> int:
    """Calcula días de mora; las facturas vigentes quedan en cero."""
    return max((as_of - due_date).days, 0)


def _monthly_totals(rows: list[MonthlyCashFlowRow]) -> dict[tuple[int, int], Decimal]:
    """Convierte filas mensuales en un mapa (año, mes) -> total."""
    return {(row.year, row.month): row.total for row in rows}


def get_niif_reports_service(db: DbSession) -> NiifReportsService:
    """Construye el servicio de estados financieros NIIF (Fase 39C)."""
    return NiifReportsService(db)


NiifReportsServiceDep = Annotated[
    NiifReportsService,
    Depends(get_niif_reports_service),
]


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


def get_budget_actuals_service(db: DbSession) -> BudgetActualsService:
    """Construye el servicio del reporte Presupuesto vs Real."""
    return BudgetActualsService(db)


BudgetActualsServiceDep = Annotated[
    BudgetActualsService,
    Depends(get_budget_actuals_service),
]


def _parse_date(value: str | None) -> date | None:
    if value is None:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Fecha inválida: {value}. Usa el formato AAAA-MM-DD",
        ) from exc


def _format_money(value: Decimal) -> str:
    """Formatea un importe decimal con dos decimales para los reportes."""
    return f"{value:.2f}"


def _natural_balance(*, debit: Decimal, credit: Decimal, nature: str) -> Decimal:
    """Convierte débitos/créditos al saldo según la naturaleza de la cuenta."""
    if nature == "DEBITO":
        return round_money(debit - credit)
    return round_money(credit - debit)


def _client_sort_key(
    client: ClientAgingAccumulator,
) -> tuple[int, Decimal, str]:
    """Ordena primero la mora más antigua y luego el saldo más alto."""
    return (-client.max_days_overdue, -client.total_balance, client.contact_name.lower())


@router.get("/aging", response_model=AgingReportResponse)
def get_aging_report(
    repository: ReportsRepositoryDep,
) -> AgingReportResponse:
    """Reporte de cartera: CxC pendientes agrupadas por días de mora.

    Se consideran únicamente facturas emitidas, no eliminadas y con saldo
    pendiente. La fecha de vencimiento efectiva es `due_date`; si no existe se
    usa `issue_date` y, como último recurso, la fecha de corte. Las facturas
    aún no vencidas se incluyen en el rango 0-30 con cero días de mora.
    """
    as_of = date.today()
    rows = repository.list_aging_invoices()

    bucket_totals: dict[str, Decimal] = {key: ZERO_MONEY for key, _ in AGING_BUCKETS}
    bucket_counts: dict[str, int] = {key: 0 for key, _ in AGING_BUCKETS}
    total_receivable = ZERO_MONEY
    clients: dict[UUID, ClientAgingAccumulator] = {}

    for row in rows:
        due_date = _effective_due_date(row, as_of)
        days_overdue = _days_overdue(due_date, as_of)
        bucket = _aging_bucket(days_overdue)

        client = clients.get(row.contact_id)
        if client is None:
            client = ClientAgingAccumulator(
                contact_id=row.contact_id,
                contact_name=row.contact_name,
            )
            clients[row.contact_id] = client

        client.total_balance = round_money(client.total_balance + row.balance)
        client.invoice_count += 1
        client.max_days_overdue = max(client.max_days_overdue, days_overdue)
        if client.oldest_due_date is None or due_date < client.oldest_due_date:
            client.oldest_due_date = due_date
        client.buckets[bucket] = round_money(client.buckets[bucket] + row.balance)

        bucket_totals[bucket] = round_money(bucket_totals[bucket] + row.balance)
        bucket_counts[bucket] += 1
        total_receivable = round_money(total_receivable + row.balance)

    client_rows = [
        AgingClientRow(
            contact_id=client.contact_id,
            contact_name=client.contact_name,
            total_balance=client.total_balance,
            max_days_overdue=client.max_days_overdue,
            oldest_due_date=client.oldest_due_date,
            invoice_count=client.invoice_count,
            buckets=client.buckets,
        )
        for client in sorted(clients.values(), key=_client_sort_key)
    ]

    bucket_rows = [
        AgingBucketSummary(
            key=key,
            label=label,
            total=bucket_totals[key],
            invoice_count=bucket_counts[key],
        )
        for key, label in AGING_BUCKETS
    ]

    return AgingReportResponse(
        as_of=as_of,
        total_receivable=total_receivable,
        buckets=bucket_rows,
        clients=client_rows,
    )


@router.get("/cash-flow", response_model=CashFlowReportResponse)
def get_cash_flow_report(
    repository: ReportsRepositoryDep,
) -> CashFlowReportResponse:
    """Flujo de caja real de los últimos seis meses y proyección a 30 días.

    Los ingresos combinan pagos de clientes y depósitos bancarios. Los egresos
    combinan pagos a proveedores, gastos y retiros bancarios. Las
    transferencias bancarias se excluyen porque son movimientos internos.

    La proyección incluye el saldo vencido más el saldo que vence dentro de los
    próximos 30 días; ambos componentes se devuelven por separado para que el
    consumidor pueda interpretar el dato.
    """
    as_of = date.today()
    first_year, first_month = _shift_month(
        as_of.year,
        as_of.month,
        -(CASH_FLOW_MONTHS - 1),
    )
    next_year, next_month = _shift_month(as_of.year, as_of.month, 1)
    start_date = date(first_year, first_month, 1)
    end_date = date(next_year, next_month, 1)

    sources = repository.get_cash_flow_sources(
        start_date=start_date,
        end_date=end_date,
    )
    customer_payments = _monthly_totals(sources.customer_payments)
    supplier_payments = _monthly_totals(sources.supplier_payments)
    expenses = _monthly_totals(sources.expenses)
    bank_deposits = _monthly_totals(sources.bank_deposits)
    bank_withdrawals = _monthly_totals(sources.bank_withdrawals)

    months: list[CashFlowMonth] = []
    for offset in range(-(CASH_FLOW_MONTHS - 1), 1):
        year, month = _shift_month(as_of.year, as_of.month, offset)
        month_key = (year, month)

        month_customer_payments = customer_payments.get(month_key, ZERO_MONEY)
        month_supplier_payments = supplier_payments.get(month_key, ZERO_MONEY)
        month_expenses = expenses.get(month_key, ZERO_MONEY)
        month_bank_deposits = bank_deposits.get(month_key, ZERO_MONEY)
        month_bank_withdrawals = bank_withdrawals.get(month_key, ZERO_MONEY)

        income = round_money(month_customer_payments + month_bank_deposits)
        month_expenses_total = round_money(
            month_supplier_payments + month_expenses + month_bank_withdrawals
        )

        months.append(
            CashFlowMonth(
                month=f"{year:04d}-{month:02d}",
                income=income,
                expenses=month_expenses_total,
                net=round_money(income - month_expenses_total),
                income_sources=CashFlowIncomeSources(
                    customer_payments=month_customer_payments,
                    bank_deposits=month_bank_deposits,
                ),
                expense_sources=CashFlowExpenseSources(
                    supplier_payments=month_supplier_payments,
                    expenses=month_expenses,
                    bank_withdrawals=month_bank_withdrawals,
                ),
            )
        )

    horizon = as_of + timedelta(days=PROJECTION_HORIZON_DAYS)
    due_within_30_days = ZERO_MONEY
    overdue_balance = ZERO_MONEY
    projection_invoice_count = 0

    for row in repository.list_aging_invoices():
        due_date = _effective_due_date(row, as_of)
        if due_date < as_of:
            overdue_balance = round_money(overdue_balance + row.balance)
            projection_invoice_count += 1
        elif due_date <= horizon:
            due_within_30_days = round_money(due_within_30_days + row.balance)
            projection_invoice_count += 1

    projection = CashFlowProjection(
        horizon_days=PROJECTION_HORIZON_DAYS,
        due_within_30_days=due_within_30_days,
        overdue_balance=overdue_balance,
        expected_collections=round_money(due_within_30_days + overdue_balance),
        invoice_count=projection_invoice_count,
    )

    return CashFlowReportResponse(
        as_of=as_of,
        months=months,
        projection=projection,
    )


def _compute_income_statement(
    repository: AccountingRepository,
    start: date | None,
    end: date | None,
) -> IncomeStatementResponse:
    """Calcula el Estado de Resultados para un rango de fechas."""
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
        .where(AccountingAccount.account_type.in_(["INGRESO", "GASTO", "COSTO"]))
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
        elif row.account_type in ("GASTO", "COSTO"):
            # El PUC distingue el costo de ventas (61) de los gastos
            # operativos (5), pero ambos se descuentan de los ingresos para
            # llegar a la utilidad neta. El esquema de respuesta solo tiene
            # dos secciones, así que los costos se presentan junto a los
            # gastos y quedan incluidos en total_expenses.
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


@router.get("/income-statement", response_model=IncomeStatementResponse)
def get_income_statement(
    repository: AccountingRepositoryDep,
    start_date: Annotated[str | None, Query()] = None,
    end_date: Annotated[str | None, Query()] = None,
    compare_with_previous: Annotated[bool, Query()] = False,
) -> IncomeStatementResponse:
    """Estado de Resultados: ingresos, costos, gastos y utilidad neta en un rango."""
    start = _parse_date(start_date)
    end = _parse_date(end_date)

    if compare_with_previous:
        # El comparativo necesita un rango explícito. Si el cliente no lo
        # envía, usamos el año en curso hasta hoy.
        if end is None:
            end = date.today()
        if start is None:
            start = date(end.year, 1, 1)
    if start is not None and end is not None and start > end:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="La fecha inicial no puede ser posterior a la fecha final",
        )

    statement = _compute_income_statement(repository, start, end)

    if compare_with_previous:
        assert start is not None and end is not None
        period_days = (end - start).days + 1
        previous_end = start - timedelta(days=1)
        previous_start = previous_end - timedelta(days=period_days - 1)
        previous = _compute_income_statement(repository, previous_start, previous_end)
        statement.previous_period = IncomeStatementPreviousPeriod(
            start_date=previous_start,
            end_date=previous_end,
            total_income=previous.total_income,
            total_expenses=previous.total_expenses,
            net_income=previous.net_income,
        )

    return statement


def _compute_balance_sheet(
    repository: AccountingRepository,
    cutoff: date | None,
) -> BalanceSheetResponse:
    """Calcula el Balance General a una fecha de corte."""
    balances = repository.get_account_balances(as_of_date=cutoff)

    asset_accounts: list[AccountReportRow] = []
    liability_accounts: list[AccountReportRow] = []
    equity_accounts: list[AccountReportRow] = []
    total_assets = Decimal("0.00")
    total_liabilities = Decimal("0.00")
    total_equity = Decimal("0.00")

    for b in balances:
        balance = b["balance"]
        if b["account_type"] == "ACTIVO":
            if b["nature"] == "CREDITO":
                # Las cuentas de activo con naturaleza crédito son contra-activos
                # (por ejemplo, 1592 Depreciación acumulada). Se presentan con
                # saldo negativo para que el total de activos sea el valor neto.
                asset_accounts.append(
                    AccountReportRow(
                        code=b["code"],
                        name=b["name"],
                        balance=_format_money(-balance),
                    )
                )
                total_assets += -balance
            elif balance < ZERO_MONEY:
                # Un activo de naturaleza débito con saldo crédito (por ejemplo,
                # un sobregiro bancario) es en sustancia un pasivo: se presenta
                # del lado del pasivo con signo positivo para no inflar activos.
                liability_accounts.append(
                    AccountReportRow(
                        code=b["code"],
                        name=b["name"],
                        balance=_format_money(-balance),
                    )
                )
                total_liabilities += -balance
            else:
                asset_accounts.append(
                    AccountReportRow(
                        code=b["code"],
                        name=b["name"],
                        balance=_format_money(balance),
                    )
                )
                total_assets += balance
        elif b["account_type"] == "PASIVO":
            if balance < ZERO_MONEY:
                # Un pasivo con saldo débito (por ejemplo, 240802 IVA
                # descontable a favor) es en sustancia un activo: se
                # reclasifica con signo positivo del lado del activo en lugar
                # de mostrar un pasivo negativo que desinfla el total.
                asset_accounts.append(
                    AccountReportRow(
                        code=b["code"],
                        name=b["name"],
                        balance=_format_money(-balance),
                    )
                )
                total_assets += -balance
            else:
                liability_accounts.append(
                    AccountReportRow(
                        code=b["code"],
                        name=b["name"],
                        balance=_format_money(balance),
                    )
                )
                total_liabilities += balance
        elif b["account_type"] == "PATRIMONIO":
            # El patrimonio con saldo débito (déficit acumulado) se sigue
            # presentando con signo negativo dentro del patrimonio.
            equity_accounts.append(
                AccountReportRow(
                    code=b["code"],
                    name=b["name"],
                    balance=_format_money(balance),
                )
            )
            total_equity += balance

    # El resultado del ejercicio (Ingresos - Gastos) se incorpora al patrimonio
    # para que el balance cuadre: Activo = Pasivo + Patrimonio + Resultado
    income_stmt = _compute_income_statement(repository, None, cutoff)
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


@router.get("/balance-sheet", response_model=BalanceSheetResponse)
def get_balance_sheet(
    repository: AccountingRepositoryDep,
    as_of_date: Annotated[str | None, Query()] = None,
    compare_with_previous: Annotated[bool, Query()] = False,
    from_date: Annotated[str | None, Query()] = None,
) -> BalanceSheetResponse:
    """Balance General: activos, pasivos, patrimonio a una fecha de corte."""
    cutoff = _parse_date(as_of_date)
    period_start = _parse_date(from_date)

    if compare_with_previous and cutoff is None:
        cutoff = date.today()
    if cutoff is not None and period_start is not None and period_start > cutoff:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="La fecha inicial no puede ser posterior a la fecha de corte",
        )

    sheet = _compute_balance_sheet(repository, cutoff)

    if compare_with_previous:
        assert cutoff is not None
        if period_start is not None:
            previous_as_of = period_start - timedelta(days=1)
        else:
            previous_as_of = cutoff - timedelta(days=365)
        previous = _compute_balance_sheet(repository, previous_as_of)
        sheet.previous_period = BalanceSheetPreviousPeriod(
            as_of_date=previous_as_of,
            total_assets=previous.total_assets,
            total_liabilities=previous.total_liabilities,
            total_equity=previous.total_equity,
            balanced=previous.balanced,
        )

    return sheet


@router.get("/ledger/accounts", response_model=list[AccountingAccountRead])
def search_ledger_accounts(
    repository: AccountingRepositoryDep,
    search: Annotated[str | None, Query(max_length=100)] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
) -> list[AccountingAccountRead]:
    """Busca cuentas PUC por código o nombre para el selector del Libro Mayor."""
    accounts = repository.search_accounts(query=search, limit=limit)
    return [AccountingAccountRead.model_validate(account) for account in accounts]


@router.get("/budget-vs-actual", response_model=BudgetVsActualReportResponse)
def get_budget_vs_actual_report(
    actuals: BudgetActualsServiceDep,
    period_year: Annotated[int, Query(ge=2000, le=2100)],
    period_month: Annotated[int, Query(ge=1, le=12)],
    cost_center_id: Annotated[UUID | None, Query()] = None,
) -> BudgetVsActualReportResponse:
    """Presupuesto vs Real: un bloque por centro de costo del periodo.

    El gasto real se deriva de las líneas contables etiquetadas con centro
    de costo (compras, gastos y nómina del mes), sin tablas paralelas.
    """
    return actuals.report_by_period(
        period_year=period_year,
        period_month=period_month,
        cost_center_id=cost_center_id,
    )


@router.get("/ledger", response_model=LedgerReportResponse)
def get_ledger(
    repository: AccountingRepositoryDep,
    account_code: Annotated[str, Query(min_length=1, max_length=20)],
    start_date: Annotated[str | None, Query()] = None,
    end_date: Annotated[str | None, Query()] = None,
) -> LedgerReportResponse:
    """Libro Mayor de una cuenta con saldo inicial, movimientos y saldo final.

    El saldo inicial suma los movimientos POSTED anteriores a ``start_date``.
    Si no se envía fecha inicial, el libro arranca en cero y muestra todo el
    historial. Los saldos se expresan según la naturaleza de la cuenta.
    """
    start = _parse_date(start_date)
    end = _parse_date(end_date)
    if start is not None and end is not None and start > end:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="La fecha inicial no puede ser posterior a la fecha final",
        )

    account = repository.get_account_by_code(account_code)
    if account is None:
        raise ResourceNotFoundError("Cuenta contable no encontrada")

    if start is None:
        opening_debit = ZERO_MONEY
        opening_credit = ZERO_MONEY
    else:
        opening_debit, opening_credit = repository.get_account_totals_before(
            account_code=account_code,
            before_date=start,
        )
    opening_balance = _natural_balance(
        debit=opening_debit,
        credit=opening_credit,
        nature=account.nature.value,
    )

    movement_rows = repository.list_account_movements(
        account_code=account_code,
        start_date=start,
        end_date=end,
    )
    running_balance = opening_balance
    total_debits = ZERO_MONEY
    total_credits = ZERO_MONEY
    movements: list[LedgerMovementRead] = []
    for row in movement_rows:
        total_debits = round_money(total_debits + row.debit)
        total_credits = round_money(total_credits + row.credit)
        running_balance = round_money(
            running_balance
            + _natural_balance(
                debit=row.debit,
                credit=row.credit,
                nature=account.nature.value,
            )
        )
        movements.append(
            LedgerMovementRead(
                id=row.id,
                entry_id=row.entry_id,
                entry_date=row.entry_date,
                description=row.description,
                source_type=row.source_type.value,
                debit=row.debit,
                credit=row.credit,
                balance=running_balance,
            )
        )

    return LedgerReportResponse(
        account_code=account.code,
        account_name=account.name,
        nature=account.nature.value,
        start_date=start,
        end_date=end,
        opening_balance=opening_balance,
        total_debits=total_debits,
        total_credits=total_credits,
        closing_balance=running_balance,
        movements=movements,
    )


@router.get("/drill-down", response_model=DrillDownResponse)
def get_drill_down(
    repository: AccountingRepositoryDep,
    account_code: Annotated[str, Query(min_length=1, max_length=20)],
    from_date: Annotated[str | None, Query()] = None,
    to_date: Annotated[str | None, Query()] = None,
) -> DrillDownResponse:
    """Auxiliar de una cuenta: movimientos y saldo acumulado del periodo."""
    start = _parse_date(from_date)
    end = _parse_date(to_date)
    if start is not None and end is not None and start > end:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="La fecha inicial no puede ser posterior a la fecha final",
        )

    account = repository.get_account_by_code(account_code)
    if account is None:
        raise ResourceNotFoundError("Cuenta contable no encontrada")

    if start is None:
        opening_debit = ZERO_MONEY
        opening_credit = ZERO_MONEY
    else:
        opening_debit, opening_credit = repository.get_account_totals_before(
            account_code=account_code,
            before_date=start,
        )
    opening_balance = _natural_balance(
        debit=opening_debit,
        credit=opening_credit,
        nature=account.nature.value,
    )

    rows = repository.list_account_movements(
        account_code=account_code,
        start_date=start,
        end_date=end,
    )
    running_balance = opening_balance
    total_debits = ZERO_MONEY
    total_credits = ZERO_MONEY
    movements: list[DrillDownMovement] = []
    for row in rows:
        total_debits = round_money(total_debits + row.debit)
        total_credits = round_money(total_credits + row.credit)
        running_balance = round_money(
            running_balance
            + _natural_balance(
                debit=row.debit,
                credit=row.credit,
                nature=account.nature.value,
            )
        )
        movements.append(
            DrillDownMovement(
                id=row.id,
                entry_id=row.entry_id,
                entry_number=f"AS-{row.entry_id.hex[:8].upper()}",
                entry_date=row.entry_date,
                description=row.description,
                debit=row.debit,
                credit=row.credit,
                balance=running_balance,
            )
        )

    return DrillDownResponse(
        account_code=account.code,
        account_name=account.name,
        nature=account.nature.value,
        from_date=start,
        to_date=end,
        opening_balance=opening_balance,
        total_debits=total_debits,
        total_credits=total_credits,
        closing_balance=running_balance,
        movements=movements,
    )


@router.get("/export/csv")
def export_financial_report_csv(
    repository: AccountingRepositoryDep,
    report: Annotated[str, Query()],
    from_date: Annotated[str | None, Query()] = None,
    to_date: Annotated[str | None, Query()] = None,
    as_of_date: Annotated[str | None, Query()] = None,
) -> StreamingResponse:
    """Exporta el Estado de Resultados o el Balance General a CSV."""
    fieldnames = ["Tipo", "Código", "Cuenta", "Saldo"]

    if report == "income-statement":
        statement = _compute_income_statement(
            repository,
            _parse_date(from_date),
            _parse_date(to_date),
        )
        rows: list[dict[str, str]] = [
            {
                "Tipo": "Ingreso",
                "Código": account.code,
                "Cuenta": account.name,
                "Saldo": account.balance,
            }
            for account in statement.income_accounts
        ]
        rows.extend(
            {
                "Tipo": "Gasto/Costo",
                "Código": account.code,
                "Cuenta": account.name,
                "Saldo": account.balance,
            }
            for account in statement.expense_accounts
        )
        rows.extend(
            [
                {
                    "Tipo": "TOTAL INGRESOS",
                    "Código": "",
                    "Cuenta": "",
                    "Saldo": statement.total_income,
                },
                {
                    "Tipo": "TOTAL GASTOS Y COSTOS",
                    "Código": "",
                    "Cuenta": "",
                    "Saldo": statement.total_expenses,
                },
                {
                    "Tipo": "UTILIDAD NETA",
                    "Código": "",
                    "Cuenta": "",
                    "Saldo": statement.net_income,
                },
            ]
        )
        filename = "estado-resultados.csv"
    elif report == "balance-sheet":
        sheet = _compute_balance_sheet(repository, _parse_date(as_of_date))
        rows = [
            {
                "Tipo": "Activo",
                "Código": account.code,
                "Cuenta": account.name,
                "Saldo": account.balance,
            }
            for account in sheet.asset_accounts
        ]
        rows.extend(
            {
                "Tipo": "Pasivo",
                "Código": account.code,
                "Cuenta": account.name,
                "Saldo": account.balance,
            }
            for account in sheet.liability_accounts
        )
        rows.extend(
            {
                "Tipo": "Patrimonio",
                "Código": account.code,
                "Cuenta": account.name,
                "Saldo": account.balance,
            }
            for account in sheet.equity_accounts
        )
        rows.extend(
            [
                {
                    "Tipo": "TOTAL ACTIVO",
                    "Código": "",
                    "Cuenta": "",
                    "Saldo": sheet.total_assets,
                },
                {
                    "Tipo": "TOTAL PASIVO",
                    "Código": "",
                    "Cuenta": "",
                    "Saldo": sheet.total_liabilities,
                },
                {
                    "Tipo": "TOTAL PATRIMONIO",
                    "Código": "",
                    "Cuenta": "",
                    "Saldo": sheet.total_equity,
                },
            ]
        )
        filename = "balance-general.csv"
    else:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="report debe ser income-statement o balance-sheet",
        )

    return StreamingResponse(
        _csv_stream(fieldnames, rows),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/export/xlsx")
def export_financial_report_xlsx(
    repository: AccountingRepositoryDep,
    report: Annotated[str, Query()],
    from_date: Annotated[str | None, Query()] = None,
    to_date: Annotated[str | None, Query()] = None,
    as_of_date: Annotated[str | None, Query()] = None,
) -> Response:
    """Exporta el Estado de Resultados o el Balance General a un XLSX formateado."""
    company = CompanySettingRepository(repository.db).get()
    company_name = company.name if company is not None else "VANTAGE"

    if report == "income-statement":
        start = _parse_date(from_date)
        end = _parse_date(to_date)
        statement = _compute_income_statement(repository, start, end)
        content = export_income_statement_xlsx(
            statement,
            company_name=company_name,
            from_date=start,
            to_date=end,
        )
        filename = "estado-resultados.xlsx"
    elif report == "balance-sheet":
        cutoff = _parse_date(as_of_date)
        sheet = _compute_balance_sheet(repository, cutoff)
        content = export_balance_sheet_xlsx(
            sheet,
            company_name=company_name,
            as_of_date=cutoff,
        )
        filename = "balance-general.xlsx"
    else:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="report debe ser income-statement o balance-sheet",
        )

    return Response(
        content=content,
        media_type=("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/trial-balance", response_model=TrialBalanceResponse)
def get_trial_balance(
    repository: AccountingRepositoryDep,
    as_of_date: Annotated[str | None, Query()] = None,
) -> TrialBalanceResponse:
    """Balance de Prueba de todas las cuentas a una fecha de corte.

    Cada fila indica si el saldo es deudor o acreedor. El reporte incluye el
    control global de partida doble: la suma de débitos debe igualar la suma de
    créditos.
    """
    cutoff = _parse_date(as_of_date)
    balances = repository.get_account_balances(as_of_date=cutoff)

    rows: list[TrialBalanceRow] = []
    total_debit = ZERO_MONEY
    total_credit = ZERO_MONEY
    for balance in balances:
        debit = round_money(balance["total_debit"])
        credit = round_money(balance["total_credit"])
        net = round_money(debit - credit)
        if net > ZERO_MONEY:
            balance_type = "DEUDOR"
        elif net < ZERO_MONEY:
            balance_type = "ACREEDOR"
        else:
            balance_type = "NEUTRO"
        rows.append(
            TrialBalanceRow(
                code=balance["code"],
                name=balance["name"],
                debit=debit,
                credit=credit,
                balance=abs(net),
                balance_type=balance_type,
            )
        )
        total_debit = round_money(total_debit + debit)
        total_credit = round_money(total_credit + credit)

    difference = round_money(total_debit - total_credit)
    return TrialBalanceResponse(
        as_of_date=cutoff,
        accounts=rows,
        total_debit=total_debit,
        total_credit=total_credit,
        difference=difference,
        balanced=difference == ZERO_MONEY,
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


@router.get("/niif/income-statement")
def get_income_statement_niif(
    service: NiifReportsServiceDep,
    from_date: Annotated[str, Query()],
    to_date: Annotated[str, Query()],
) -> dict[str, object]:
    """Estado de Resultados NIIF por función (Decimal, del PUC 4/5/6)."""
    return service.income_statement_niif(
        from_date=_parse_date(from_date) or date.today(),
        to_date=_parse_date(to_date) or date.today(),
    )


@router.get("/niif/balance-sheet")
def get_balance_sheet_niif(
    service: NiifReportsServiceDep,
    as_of_date: Annotated[str, Query()],
) -> dict[str, object]:
    """Balance General NIIF: corriente/no corriente + ecuación verificada."""
    return service.balance_sheet_niif(
        as_of_date=_parse_date(as_of_date) or date.today(),
    )


@router.get("/niif/cash-flow")
def get_cash_flow_niif(
    service: NiifReportsServiceDep,
    from_date: Annotated[str, Query()],
    to_date: Annotated[str, Query()],
) -> dict[str, object]:
    """Flujo de Efectivo por método indirecto (variación de capital de trabajo)."""
    return service.cash_flow_niif(
        from_date=_parse_date(from_date) or date.today(),
        to_date=_parse_date(to_date) or date.today(),
    )
