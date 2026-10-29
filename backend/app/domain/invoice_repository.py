"""Repositorio de facturas con SQLAlchemy 2."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session, selectinload

from app.domain.exceptions import InvoiceStateError, ResourceNotFoundError
from app.domain.models.idempotency_key import IdempotencyKey
from app.domain.models.invoice import Invoice, LifecycleStatus, PaymentStatus
from app.domain.models.invoice_line import InvoiceLine
from app.domain.models.number_sequence import NumberSequence
from app.domain.models.payment import Payment
from app.infrastructure.tenancy import require_company_id

INVOICE_SEQUENCE_NAME = "invoice"
INVOICE_SEQUENCE_PREFIX = "FV"


@dataclass(frozen=True)
class NewInvoiceLine:
    """Línea ya calculada y lista para persistir."""

    item_id: UUID
    description: str
    quantity: Decimal
    unit_price: Decimal
    discount_percent: Decimal
    tax_rate: Decimal
    subtotal: Decimal
    tax: Decimal
    total: Decimal


class InvoiceRepository:
    """Acceso a facturas y a las tablas auxiliares de emisión."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def create_draft(
        self,
        *,
        contact_id: UUID,
        issue_date: date,
        due_date: date,
        currency: str,
        lines: list[NewInvoiceLine],
        subtotal: Decimal,
        tax_total: Decimal,
        total: Decimal,
        payment_mean_code: str | None = None,
    ) -> Invoice:
        """Crea una factura DRAFT/UNPAID con sus líneas, sin número."""
        invoice = Invoice(
            number=None,
            contact_id=contact_id,
            issue_date=issue_date,
            due_date=due_date,
            currency=currency,
            payment_mean_code=payment_mean_code,
            lifecycle_status=LifecycleStatus.DRAFT,
            payment_status=PaymentStatus.UNPAID,
            subtotal=subtotal,
            tax_total=tax_total,
            total=total,
            balance=total,
        )
        invoice.lines = [
            InvoiceLine(
                item_id=line.item_id,
                description=line.description,
                quantity=line.quantity,
                unit_price=line.unit_price,
                discount_percent=line.discount_percent,
                tax_rate=line.tax_rate,
                line_subtotal=line.subtotal,
                line_tax=line.tax,
                line_total=line.total,
            )
            for line in lines
        ]
        self.db.add(invoice)
        self.db.flush()
        self.db.refresh(invoice)
        return invoice

    def get_by_id(self, invoice_id: UUID) -> Invoice | None:
        statement = (
            select(Invoice)
            .where(Invoice.id == invoice_id, Invoice.deleted_at.is_(None))
            .options(
                selectinload(Invoice.contact),
                selectinload(Invoice.lines),
            )
        )
        return self.db.scalar(statement)

    def list(self, limit: int, offset: int) -> list[Invoice]:
        """Lista facturas no eliminadas."""
        statement = (
            select(Invoice)
            .where(Invoice.deleted_at.is_(None))
            .options(
                selectinload(Invoice.contact),
                selectinload(Invoice.lines),
            )
            .order_by(Invoice.created_at.desc(), Invoice.id)
            .limit(limit)
            .offset(offset)
        )
        return list(self.db.scalars(statement).all())

    def issue(self, invoice_id: UUID) -> Invoice:
        """Emite una factura DRAFT y asigna el siguiente número.

        REQUIERE VALIDACIÓN: contador/experto DIAN. El prefijo FV, el rango de
        numeración y el formato de ocho dígitos son una decisión provisional del
        MVP; la numeración autorizada debe venir de la resolución configurada.
        """
        invoice = self.db.scalar(
            select(Invoice)
            .where(Invoice.id == invoice_id, Invoice.deleted_at.is_(None))
            .with_for_update()
        )
        if invoice is None:
            raise ResourceNotFoundError("Factura no encontrada")
        if invoice.lifecycle_status is not LifecycleStatus.DRAFT:
            raise InvoiceStateError("Solo se emiten facturas en estado borrador")

        sequence = self.db.scalar(
            select(NumberSequence)
            .where(NumberSequence.name == INVOICE_SEQUENCE_NAME)
            .with_for_update()
        )
        if sequence is None:
            # on_conflict evita que dos emisiones concurrentes creen la fila dos veces.
            self.db.execute(
                pg_insert(NumberSequence)
                .values(
                    company_id=require_company_id(self.db),
                    name=INVOICE_SEQUENCE_NAME,
                    prefix=INVOICE_SEQUENCE_PREFIX,
                    next_number=1,
                )
                .on_conflict_do_nothing(index_elements=["company_id", "name"])
            )
            sequence = self.db.scalar(
                select(NumberSequence)
                .where(NumberSequence.name == INVOICE_SEQUENCE_NAME)
                .with_for_update()
            )
            if sequence is None:
                raise RuntimeError("No se pudo crear la secuencia de facturas")

        invoice.number = f"{sequence.prefix}{sequence.next_number:08d}"
        sequence.next_number += 1
        invoice.lifecycle_status = LifecycleStatus.ISSUED
        invoice.version += 1
        invoice.updated_at = datetime.now(UTC)

        # La capa de API confirma la transacción después de generar el asiento
        # contable; así emisión y contabilidad son atómicas.
        self.db.flush()
        return invoice

    def void_invoice(self, invoice_id: UUID, reason: str) -> Invoice:
        """Anula una factura emitida sin pagos, bloqueando la fila.

        El lock serializa este void con pagos y con otros voids concurrentes.
        No modifica payment_status: en el MVP solo se anulan facturas sin pagos.
        """
        invoice = self.db.scalar(
            select(Invoice)
            .where(Invoice.id == invoice_id, Invoice.deleted_at.is_(None))
            .with_for_update()
        )
        if invoice is None:
            raise ResourceNotFoundError("Factura no encontrada")
        if invoice.lifecycle_status is LifecycleStatus.DRAFT:
            raise InvoiceStateError("No se puede anular un borrador, elimínelo")
        if invoice.lifecycle_status is LifecycleStatus.VOID:
            raise InvoiceStateError("Factura ya anulada")

        payment_id = self.db.scalar(
            select(Payment.id).where(Payment.invoice_id == invoice_id).limit(1)
        )
        if payment_id is not None:
            raise InvoiceStateError("Factura con pagos. Use nota crédito (no implementada en MVP)")

        now = datetime.now(UTC)
        invoice.lifecycle_status = LifecycleStatus.VOID
        invoice.voided_reason = reason
        invoice.voided_at = now
        invoice.version += 1
        invoice.updated_at = now

        # La API genera el contra-asiento y confirma en la misma transacción.
        self.db.flush()
        return invoice

    def delete_draft(self, invoice_id: UUID) -> None:
        """Elimina lógicamente una factura DRAFT.

        La fila se conserva con deleted_at para que GET y LIST la excluyan. Solo
        se permite sobre borradores; emitidas y anuladas responden 409.
        """
        invoice = self.db.scalar(
            select(Invoice)
            .where(Invoice.id == invoice_id, Invoice.deleted_at.is_(None))
            .with_for_update()
        )
        if invoice is None:
            raise ResourceNotFoundError("Factura no encontrada")
        if invoice.lifecycle_status is not LifecycleStatus.DRAFT:
            raise InvoiceStateError("Solo se eliminan borradores")

        now = datetime.now(UTC)
        invoice.deleted_at = now
        invoice.version += 1
        invoice.updated_at = now
        self.db.commit()

    def get_idempotency_key(self, key: str) -> IdempotencyKey | None:
        """Busca una clave de idempotencia por su valor."""
        return self.db.scalar(select(IdempotencyKey).where(IdempotencyKey.key == key))

    def add_idempotency_key(
        self,
        *,
        key: str,
        request_hash: str,
        response_body: dict[str, Any],
    ) -> None:
        """Registra la respuesta para futuras repeticiones de la misma clave."""
        self.db.add(
            IdempotencyKey(
                key=key,
                request_hash=request_hash,
                response_body=response_body,
            )
        )

    def commit(self) -> None:
        """Confirma la transacción en curso."""
        self.db.commit()

    def rollback(self) -> None:
        """Revierte la transacción en curso."""
        self.db.rollback()
