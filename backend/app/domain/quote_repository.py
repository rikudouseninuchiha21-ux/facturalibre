"""Repositorio de cotizaciones con SQLAlchemy 2."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any, cast
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.engine import CursorResult
from sqlalchemy.orm import Session, selectinload

from app.domain.exceptions import QuoteStateError, ResourceNotFoundError
from app.domain.models.contact import Contact
from app.domain.models.idempotency_key import IdempotencyKey
from app.domain.models.quote import Quote, QuoteStatus
from app.domain.models.quote_line import QuoteLine

QUOTE_SEQUENCE_NAME = "quote"
QUOTE_SEQUENCE_PREFIX = "QT"


@dataclass(frozen=True)
class NewQuoteLine:
    """Línea ya calculada y lista para persistir."""

    item_id: UUID
    description: str
    quantity: Decimal
    unit_price: Decimal
    tax_rate: Decimal
    subtotal: Decimal
    tax: Decimal
    total: Decimal


class QuoteRepository:
    """Acceso a datos de cotizaciones; excluye soft-deleted por defecto."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def create_draft(
        self,
        *,
        contact_id: UUID,
        issue_date: date,
        expiry_date: date,
        currency: str,
        lines: list[NewQuoteLine],
        subtotal: Decimal,
        tax_total: Decimal,
        total: Decimal,
    ) -> Quote:
        """Crea una cotización DRAFT con sus líneas, sin número."""
        quote = Quote(
            number=None,
            contact_id=contact_id,
            issue_date=issue_date,
            expiry_date=expiry_date,
            currency=currency,
            status=QuoteStatus.DRAFT,
            subtotal=subtotal,
            tax_total=tax_total,
            total=total,
        )
        quote.lines = [
            QuoteLine(
                item_id=line.item_id,
                description=line.description,
                quantity=line.quantity,
                unit_price=line.unit_price,
                tax_rate=line.tax_rate,
                line_subtotal=line.subtotal,
                line_tax=line.tax,
                line_total=line.total,
            )
            for line in lines
        ]
        self.db.add(quote)
        self.db.flush()
        self.db.refresh(quote)
        return quote

    def get_by_id(self, quote_id: UUID) -> tuple[Quote, str] | None:
        """Obtiene una cotización con sus líneas y el nombre del contacto."""
        statement = (
            select(Quote, Contact.name)
            .join(Contact, Contact.id == Quote.contact_id)
            .where(Quote.id == quote_id, Quote.deleted_at.is_(None))
            .options(selectinload(Quote.lines))
        )
        return self.db.execute(statement).first()

    def list(self, limit: int, offset: int) -> list[tuple[Quote, str]]:
        """Lista cotizaciones no eliminadas con el nombre del contacto."""
        statement = (
            select(Quote, Contact.name)
            .join(Contact, Contact.id == Quote.contact_id)
            .where(Quote.deleted_at.is_(None))
            .options(selectinload(Quote.lines))
            .order_by(Quote.created_at.desc(), Quote.id)
            .limit(limit)
            .offset(offset)
        )
        return list(self.db.execute(statement).all())

    def update_status(
        self,
        quote_id: UUID,
        expected_status: QuoteStatus,
        new_status: QuoteStatus,
    ) -> Quote:
        """Cambia el estado de una cotización (bloqueo optimista por estado)."""
        quote = self.db.scalar(
            select(Quote).where(Quote.id == quote_id, Quote.deleted_at.is_(None)).with_for_update()
        )
        if quote is None:
            raise ResourceNotFoundError("Cotización no encontrada")
        if quote.status is not expected_status:
            raise QuoteStateError(
                f"La cotización está en {quote.status.value}, se esperaba {expected_status.value}"
            )
        quote.status = new_status
        quote.version += 1
        quote.updated_at = datetime.now(UTC)
        self.db.flush()
        return quote

    def soft_delete(self, quote_id: UUID) -> None:
        """Elimina lógicamente una cotización (solo borradores)."""
        quote = self.db.scalar(
            select(Quote).where(Quote.id == quote_id, Quote.deleted_at.is_(None)).with_for_update()
        )
        if quote is None:
            raise ResourceNotFoundError("Cotización no encontrada")
        if quote.status is not QuoteStatus.DRAFT:
            raise QuoteStateError("Solo se eliminan cotizaciones en borrador")

        now = datetime.now(UTC)
        quote.deleted_at = now
        quote.version += 1
        quote.updated_at = now
        self.db.flush()

    def set_converted_invoice(self, quote_id: UUID, invoice_id: UUID) -> None:
        """Asigna la factura generada al convertir y marca la cotización."""
        statement = (
            update(Quote)
            .where(Quote.id == quote_id, Quote.deleted_at.is_(None))
            .values(
                converted_invoice_id=invoice_id,
                status=QuoteStatus.CONVERTED,
                version=Quote.version + 1,
                updated_at=func.now(),
            )
        )
        result = cast(CursorResult[Any], self.db.execute(statement))
        if result.rowcount == 0:
            raise ResourceNotFoundError("Cotización no encontrada")

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
