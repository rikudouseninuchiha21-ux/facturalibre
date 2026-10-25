"""Consultas de solo lectura para exportar reportes a CSV y de cartera."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.domain.calculations import ZERO_MONEY, round_money
from app.domain.models.bank import BankTransaction, BankTransactionType
from app.domain.models.contact import Contact
from app.domain.models.expense import Expense
from app.domain.models.invoice import Invoice, LifecycleStatus
from app.domain.models.payment import Payment
from app.domain.models.purchase import PurchasePayment


@dataclass(frozen=True)
class InvoiceExportRow:
    number: str | None
    issue_date: date | None
    contact_name: str
    subtotal: Decimal
    tax_total: Decimal
    total: Decimal
    lifecycle_status: LifecycleStatus


@dataclass(frozen=True)
class PaymentExportRow:
    invoice_number: str | None
    payment_date: date
    amount: Decimal
    method: str


@dataclass(frozen=True)
class AgingInvoiceRow:
    """Factura emitida con saldo pendiente y su fecha de vencimiento."""

    invoice_id: UUID
    invoice_number: str | None
    contact_id: UUID
    contact_name: str
    issue_date: date | None
    due_date: date | None
    balance: Decimal


@dataclass(frozen=True)
class MonthlyCashFlowRow:
    """Total de una fuente de caja para un mes calendario."""

    year: int
    month: int
    total: Decimal


@dataclass(frozen=True)
class CashFlowSourceRows:
    """Totales mensuales separados por fuente de ingreso o egreso."""

    customer_payments: list[MonthlyCashFlowRow]
    supplier_payments: list[MonthlyCashFlowRow]
    expenses: list[MonthlyCashFlowRow]
    bank_deposits: list[MonthlyCashFlowRow]
    bank_withdrawals: list[MonthlyCashFlowRow]


def _as_money(value: object | None) -> Decimal:
    """Normaliza agregados SQL, que pueden llegar como Decimal o None."""
    if value is None:
        return ZERO_MONEY
    if isinstance(value, Decimal):
        return round_money(value)
    return round_money(Decimal(str(value)))


class ReportsRepository:
    """Acceso de solo lectura a datos para exportación de reportes."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def list_invoices_for_export(self) -> list[InvoiceExportRow]:
        """Devuelve facturas no eliminadas con los datos del reporte CSV."""
        statement = (
            select(
                Invoice.number,
                Invoice.issue_date,
                Contact.name,
                Invoice.subtotal,
                Invoice.tax_total,
                Invoice.total,
                Invoice.lifecycle_status,
            )
            .join(Contact, Contact.id == Invoice.contact_id)
            .where(Invoice.deleted_at.is_(None))
            .order_by(
                Invoice.issue_date.desc().nullslast(),
                Invoice.created_at.desc(),
                Invoice.id,
            )
        )
        rows = self.db.execute(statement).all()
        return [
            InvoiceExportRow(
                number=row[0],
                issue_date=row[1],
                contact_name=row[2],
                subtotal=row[3],
                tax_total=row[4],
                total=row[5],
                lifecycle_status=row[6],
            )
            for row in rows
        ]

    def list_payments_for_export(self) -> list[PaymentExportRow]:
        """Devuelve pagos con los datos del reporte CSV."""
        statement = (
            select(
                Invoice.number,
                Payment.payment_date,
                Payment.amount,
                Payment.method,
            )
            .join(Invoice, Invoice.id == Payment.invoice_id)
            .where(Invoice.deleted_at.is_(None))
            .order_by(Payment.payment_date.desc(), Payment.id.desc())
        )
        rows = self.db.execute(statement).all()
        return [
            PaymentExportRow(
                invoice_number=row[0],
                payment_date=row[1],
                amount=row[2],
                method=row[3],
            )
            for row in rows
        ]

    def list_aging_invoices(self) -> list[AgingInvoiceRow]:
        """Devuelve las CxC pendientes de facturas emitidas y no eliminadas."""
        statement = (
            select(
                Invoice.id,
                Invoice.number,
                Invoice.contact_id,
                Contact.name,
                Invoice.issue_date,
                Invoice.due_date,
                Invoice.balance,
            )
            .join(Contact, Contact.id == Invoice.contact_id)
            .where(
                Invoice.lifecycle_status == LifecycleStatus.ISSUED,
                Invoice.deleted_at.is_(None),
                Invoice.balance > ZERO_MONEY,
            )
            .order_by(
                Invoice.due_date.asc().nullslast(),
                Invoice.issue_date.asc().nullslast(),
                Invoice.id,
            )
        )
        rows = self.db.execute(statement).all()
        return [
            AgingInvoiceRow(
                invoice_id=row[0],
                invoice_number=row[1],
                contact_id=row[2],
                contact_name=row[3],
                issue_date=row[4],
                due_date=row[5],
                balance=_as_money(row[6]),
            )
            for row in rows
        ]

    def get_cash_flow_sources(
        self,
        *,
        start_date: date,
        end_date: date,
    ) -> CashFlowSourceRows:
        """Agrega por mes las fuentes de caja reales del período solicitado.

        Las transferencias bancarias se excluyen porque son movimientos
        internos entre cuentas de la misma empresa y no representan ingreso ni
        egreso económico.
        """
        payment_year = func.extract("year", Payment.payment_date)
        payment_month = func.extract("month", Payment.payment_date)
        customer_payment_rows = self.db.execute(
            select(
                payment_year,
                payment_month,
                func.coalesce(func.sum(Payment.amount), ZERO_MONEY),
            )
            .where(
                Payment.payment_date >= start_date,
                Payment.payment_date < end_date,
            )
            .group_by(payment_year, payment_month)
            .order_by(payment_year, payment_month)
        ).all()

        supplier_year = func.extract("year", PurchasePayment.payment_date)
        supplier_month = func.extract("month", PurchasePayment.payment_date)
        supplier_payment_rows = self.db.execute(
            select(
                supplier_year,
                supplier_month,
                func.coalesce(func.sum(PurchasePayment.amount), ZERO_MONEY),
            )
            .where(
                PurchasePayment.payment_date >= start_date,
                PurchasePayment.payment_date < end_date,
            )
            .group_by(supplier_year, supplier_month)
            .order_by(supplier_year, supplier_month)
        ).all()

        expense_year = func.extract("year", Expense.date)
        expense_month = func.extract("month", Expense.date)
        expense_rows = self.db.execute(
            select(
                expense_year,
                expense_month,
                func.coalesce(func.sum(Expense.amount), ZERO_MONEY),
            )
            .where(
                Expense.date >= start_date,
                Expense.date < end_date,
                Expense.deleted_at.is_(None),
            )
            .group_by(expense_year, expense_month)
            .order_by(expense_year, expense_month)
        ).all()

        bank_year = func.extract("year", BankTransaction.date)
        bank_month = func.extract("month", BankTransaction.date)
        bank_deposit_rows = self.db.execute(
            select(
                bank_year,
                bank_month,
                func.coalesce(func.sum(BankTransaction.amount), ZERO_MONEY),
            )
            .where(
                BankTransaction.date >= start_date,
                BankTransaction.date < end_date,
                BankTransaction.deleted_at.is_(None),
                BankTransaction.transaction_type == BankTransactionType.DEPOSIT,
            )
            .group_by(bank_year, bank_month)
            .order_by(bank_year, bank_month)
        ).all()

        bank_withdrawal_rows = self.db.execute(
            select(
                bank_year,
                bank_month,
                func.coalesce(func.sum(BankTransaction.amount), ZERO_MONEY),
            )
            .where(
                BankTransaction.date >= start_date,
                BankTransaction.date < end_date,
                BankTransaction.deleted_at.is_(None),
                BankTransaction.transaction_type == BankTransactionType.WITHDRAWAL,
            )
            .group_by(bank_year, bank_month)
            .order_by(bank_year, bank_month)
        ).all()

        return CashFlowSourceRows(
            customer_payments=[
                MonthlyCashFlowRow(
                    year=int(year),
                    month=int(month),
                    total=_as_money(total),
                )
                for year, month, total in customer_payment_rows
            ],
            supplier_payments=[
                MonthlyCashFlowRow(
                    year=int(year),
                    month=int(month),
                    total=_as_money(total),
                )
                for year, month, total in supplier_payment_rows
            ],
            expenses=[
                MonthlyCashFlowRow(
                    year=int(year),
                    month=int(month),
                    total=_as_money(total),
                )
                for year, month, total in expense_rows
            ],
            bank_deposits=[
                MonthlyCashFlowRow(
                    year=int(year),
                    month=int(month),
                    total=_as_money(total),
                )
                for year, month, total in bank_deposit_rows
            ],
            bank_withdrawals=[
                MonthlyCashFlowRow(
                    year=int(year),
                    month=int(month),
                    total=_as_money(total),
                )
                for year, month, total in bank_withdrawal_rows
            ],
        )
