"""Consultas de solo lectura para exportar reportes a CSV."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.models.contact import Contact
from app.domain.models.invoice import Invoice, LifecycleStatus
from app.domain.models.payment import Payment


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
