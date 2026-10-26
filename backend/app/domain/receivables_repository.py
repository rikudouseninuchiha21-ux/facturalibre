"""Acceso a datos de cartera (aging, estado de cuenta, recordatorios, acuerdos).

Las consultas de aging usan agregados por factura (``SUM(payments)`` y
``SUM(credit_notes emitidas)``) en subconsultas, de modo que se ejecutan en
un número constante de queries sin N+1 por factura.

Ningún método hace commit: la capa de API controla la transacción con
``operation_transaction``.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.domain.calculations import round_money
from app.domain.models.contact import Contact
from app.domain.models.credit_note import CreditNote, CreditNoteStatus
from app.domain.models.invoice import Invoice, LifecycleStatus
from app.domain.models.payment import Payment
from app.domain.models.receivables import (
    AgreementStatus,
    PaymentAgreement,
    PaymentAgreementInstallment,
    PaymentReminder,
)

ZERO = Decimal("0.00")


@dataclass(frozen=True)
class OutstandingInvoiceRow:
    """Factura emitida con saldo pendiente derivado de pagos y notas crédito."""

    invoice_id: UUID
    number: str | None
    contact_id: UUID
    contact_name: str
    issue_date: date | None
    due_date: date | None
    total: Decimal
    outstanding: Decimal
    created_at: datetime


@dataclass(frozen=True)
class StatementInvoiceRow:
    """Factura emitida incluida en un estado de cuenta."""

    invoice_id: UUID
    number: str | None
    issue_date: date | None
    total: Decimal
    created_at: datetime


@dataclass(frozen=True)
class StatementPaymentRow:
    """Pago recibido incluido en un estado de cuenta."""

    payment_id: UUID
    invoice_id: UUID
    invoice_number: str | None
    payment_date: date
    amount: Decimal
    method: str
    reference: str | None


@dataclass(frozen=True)
class StatementCreditNoteRow:
    """Nota crédito emitida incluida en un estado de cuenta."""

    credit_note_id: UUID
    invoice_id: UUID
    invoice_number: str | None
    issue_date: date | None
    number: str | None
    total: Decimal
    created_at: datetime


class ReceivablesRepository:
    """Consultas de cartera y persistencia de recordatorios y acuerdos."""

    def __init__(self, db: Session) -> None:
        self.db = db

    # -- Lecturas de cartera ---------------------------------------------

    def get_contact(self, contact_id: UUID) -> Contact | None:
        """Contacto activo (no eliminado lógicamente)."""
        return self.db.scalar(
            select(Contact).where(
                Contact.id == contact_id,
                Contact.deleted_at.is_(None),
            )
        )

    def list_outstanding_invoices(self, *, as_of_date: date) -> list[OutstandingInvoiceRow]:
        """Facturas ISSUED con saldo > 0 a la fecha de corte, en una sola query.

        El saldo se deriva de la fuente real de movimientos:
        ``total - SUM(payments) - SUM(credit_notes emitidas)``.
        """
        paid = (
            select(
                Payment.invoice_id.label("invoice_id"),
                func.coalesce(func.sum(Payment.amount), ZERO).label("paid_total"),
            )
            .group_by(Payment.invoice_id)
            .subquery()
        )
        credited = (
            select(
                CreditNote.invoice_id.label("invoice_id"),
                func.coalesce(func.sum(CreditNote.total), ZERO).label("credit_total"),
            )
            .where(CreditNote.status == CreditNoteStatus.ISSUED)
            .group_by(CreditNote.invoice_id)
            .subquery()
        )

        paid_total = func.coalesce(paid.c.paid_total, ZERO)
        credit_total = func.coalesce(credited.c.credit_total, ZERO)
        outstanding = Invoice.total - paid_total - credit_total

        statement = (
            select(
                Invoice.id,
                Invoice.number,
                Invoice.contact_id,
                Contact.name,
                Invoice.issue_date,
                Invoice.due_date,
                Invoice.total,
                outstanding.label("outstanding"),
                Invoice.created_at,
            )
            .join(Contact, Contact.id == Invoice.contact_id)
            .outerjoin(paid, paid.c.invoice_id == Invoice.id)
            .outerjoin(credited, credited.c.invoice_id == Invoice.id)
            .where(
                Invoice.lifecycle_status == LifecycleStatus.ISSUED,
                Invoice.deleted_at.is_(None),
                Invoice.issue_date.is_not(None),
                Invoice.issue_date <= as_of_date,
                outstanding > ZERO,
            )
            .order_by(Invoice.issue_date, Invoice.id)
        )

        rows = self.db.execute(statement).all()
        return [
            OutstandingInvoiceRow(
                invoice_id=row.id,
                number=row.number,
                contact_id=row.contact_id,
                contact_name=row.name,
                issue_date=row.issue_date,
                due_date=row.due_date,
                total=round_money(row.total),
                outstanding=round_money(row.outstanding),
                created_at=row.created_at,
            )
            for row in rows
        ]

    def statement_invoices(
        self,
        *,
        contact_id: UUID,
        to_date: date,
    ) -> list[StatementInvoiceRow]:
        """Facturas emitidas del contacto hasta la fecha final (inclusive)."""
        statement = (
            select(
                Invoice.id,
                Invoice.number,
                Invoice.issue_date,
                Invoice.total,
                Invoice.created_at,
            )
            .where(
                Invoice.contact_id == contact_id,
                Invoice.lifecycle_status == LifecycleStatus.ISSUED,
                Invoice.deleted_at.is_(None),
                or_(Invoice.issue_date.is_(None), Invoice.issue_date <= to_date),
            )
            .order_by(Invoice.issue_date, Invoice.id)
        )
        return [
            StatementInvoiceRow(
                invoice_id=row.id,
                number=row.number,
                issue_date=row.issue_date,
                total=round_money(row.total),
                created_at=row.created_at,
            )
            for row in self.db.execute(statement).all()
        ]

    def statement_payments(
        self,
        *,
        contact_id: UUID,
        to_date: date,
    ) -> list[StatementPaymentRow]:
        """Pagos de facturas del contacto hasta la fecha final."""
        statement = (
            select(
                Payment.id,
                Payment.invoice_id,
                Invoice.number,
                Payment.payment_date,
                Payment.amount,
                Payment.method,
                Payment.reference,
            )
            .join(Invoice, Invoice.id == Payment.invoice_id)
            .where(
                Invoice.contact_id == contact_id,
                Invoice.lifecycle_status == LifecycleStatus.ISSUED,
                Invoice.deleted_at.is_(None),
                Payment.payment_date <= to_date,
            )
            .order_by(Payment.payment_date, Payment.id)
        )
        return [
            StatementPaymentRow(
                payment_id=row.id,
                invoice_id=row.invoice_id,
                invoice_number=row.number,
                payment_date=row.payment_date,
                amount=round_money(row.amount),
                method=row.method,
                reference=row.reference,
            )
            for row in self.db.execute(statement).all()
        ]

    def statement_credit_notes(
        self,
        *,
        contact_id: UUID,
        to_date: date,
    ) -> list[StatementCreditNoteRow]:
        """Notas crédito emitidas de facturas del contacto hasta la fecha final."""
        statement = (
            select(
                CreditNote.id,
                CreditNote.invoice_id,
                Invoice.number,
                CreditNote.issue_date,
                CreditNote.number,
                CreditNote.total,
                CreditNote.created_at,
            )
            .join(Invoice, Invoice.id == CreditNote.invoice_id)
            .where(
                Invoice.contact_id == contact_id,
                Invoice.lifecycle_status == LifecycleStatus.ISSUED,
                Invoice.deleted_at.is_(None),
                CreditNote.status == CreditNoteStatus.ISSUED,
                or_(CreditNote.issue_date.is_(None), CreditNote.issue_date <= to_date),
            )
            .order_by(CreditNote.issue_date, CreditNote.id)
        )
        return [
            StatementCreditNoteRow(
                credit_note_id=row.id,
                invoice_id=row.invoice_id,
                invoice_number=row.number,
                issue_date=row.issue_date,
                number=row.number_1,
                total=round_money(row.total),
                created_at=row.created_at,
            )
            for row in self.db.execute(statement).all()
        ]

    def get_invoice(self, invoice_id: UUID) -> Invoice | None:
        """Factura no eliminada, con su contacto cargado."""
        return self.db.scalar(
            select(Invoice)
            .where(Invoice.id == invoice_id, Invoice.deleted_at.is_(None))
            .options(selectinload(Invoice.contact))
        )

    def outstanding_for_invoice(self, invoice: Invoice) -> Decimal:
        """Saldo pendiente de una factura concreta (derivado, sin N+1)."""
        paid = self.db.scalar(
            select(func.coalesce(func.sum(Payment.amount), ZERO)).where(
                Payment.invoice_id == invoice.id
            )
        )
        credited = self.db.scalar(
            select(func.coalesce(func.sum(CreditNote.total), ZERO)).where(
                CreditNote.invoice_id == invoice.id,
                CreditNote.status == CreditNoteStatus.ISSUED,
            )
        )
        value = invoice.total - (paid or ZERO) - (credited or ZERO)
        return round_money(value) if value > ZERO else ZERO

    # -- Recordatorios ----------------------------------------------------

    def has_reminder_since(
        self,
        *,
        invoice_id: UUID,
        level: int,
        since: datetime,
    ) -> bool:
        """Indica si ya existe un recordatorio del mismo nivel desde ``since``."""
        return (
            self.db.scalar(
                select(PaymentReminder.id)
                .where(
                    PaymentReminder.invoice_id == invoice_id,
                    PaymentReminder.level == level,
                    PaymentReminder.sent_at >= since,
                )
                .limit(1)
            )
            is not None
        )

    def remindable_invoice_ids(
        self,
        *,
        since: datetime,
    ) -> set[tuple[UUID, int]]:
        """Pares (invoice_id, level) con recordatorio dentro de la ventana."""
        rows = self.db.execute(
            select(PaymentReminder.invoice_id, PaymentReminder.level).where(
                PaymentReminder.sent_at >= since
            )
        ).all()
        return {(row.invoice_id, row.level) for row in rows}

    def create_reminder(self, values: dict[str, Any]) -> PaymentReminder:
        reminder = PaymentReminder(**values)
        self.db.add(reminder)
        self.db.flush()
        self.db.refresh(reminder)
        return reminder

    def list_reminders(
        self,
        *,
        invoice_id: UUID | None = None,
        contact_id: UUID | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[PaymentReminder]:
        statement = select(PaymentReminder).order_by(
            PaymentReminder.sent_at.desc(),
            PaymentReminder.id,
        )
        if invoice_id is not None:
            statement = statement.where(PaymentReminder.invoice_id == invoice_id)
        if contact_id is not None:
            statement = statement.where(PaymentReminder.contact_id == contact_id)
        statement = statement.limit(limit).offset(offset)
        return list(self.db.scalars(statement).all())

    # -- Acuerdos ---------------------------------------------------------

    def create_agreement(
        self,
        *,
        values: dict[str, Any],
        installments: list[PaymentAgreementInstallment],
    ) -> PaymentAgreement:
        agreement = PaymentAgreement(**values)
        agreement.installment_items = installments
        self.db.add(agreement)
        self.db.flush()
        self.db.refresh(agreement)
        return agreement

    def get_agreement(self, agreement_id: UUID) -> PaymentAgreement | None:
        return self.db.scalar(
            select(PaymentAgreement)
            .where(PaymentAgreement.id == agreement_id)
            .options(selectinload(PaymentAgreement.installment_items))
        )

    def list_agreements(
        self,
        *,
        contact_id: UUID | None = None,
        status: AgreementStatus | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[PaymentAgreement]:
        statement = (
            select(PaymentAgreement)
            .options(selectinload(PaymentAgreement.installment_items))
            .order_by(PaymentAgreement.created_at.desc(), PaymentAgreement.id)
        )
        if contact_id is not None:
            statement = statement.where(PaymentAgreement.contact_id == contact_id)
        if status is not None:
            statement = statement.where(PaymentAgreement.status == status)
        statement = statement.limit(limit).offset(offset)
        return list(self.db.scalars(statement).all())

    def get_installment_for_update(
        self,
        *,
        agreement_id: UUID,
        installment_id: UUID,
    ) -> PaymentAgreementInstallment | None:
        return self.db.scalar(
            select(PaymentAgreementInstallment)
            .where(
                PaymentAgreementInstallment.id == installment_id,
                PaymentAgreementInstallment.agreement_id == agreement_id,
            )
            .with_for_update()
        )

    def get_agreement_for_update(self, agreement_id: UUID) -> PaymentAgreement | None:
        return self.db.scalar(
            select(PaymentAgreement)
            .where(PaymentAgreement.id == agreement_id)
            .options(selectinload(PaymentAgreement.installment_items))
            .with_for_update()
        )


__all__ = [
    "OutstandingInvoiceRow",
    "ReceivablesRepository",
    "StatementCreditNoteRow",
    "StatementInvoiceRow",
    "StatementPaymentRow",
]
