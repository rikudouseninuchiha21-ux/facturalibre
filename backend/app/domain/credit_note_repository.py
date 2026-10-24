"""Repositorio de notas crédito con SQLAlchemy 2."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session, selectinload

from app.domain.exceptions import ResourceNotFoundError
from app.domain.models.credit_note import CreditNote, CreditNoteLine, CreditNoteStatus
from app.domain.models.idempotency_key import IdempotencyKey
from app.domain.models.number_sequence import NumberSequence

CREDIT_NOTE_SEQUENCE_NAME = "credit_note"
CREDIT_NOTE_SEQUENCE_PREFIX = "NC"


@dataclass(frozen=True)
class NewCreditNoteLine:
    """Línea ya calculada y lista para persistir."""

    invoice_line_id: UUID | None
    description: str
    quantity: Decimal
    unit_price: Decimal
    tax_rate: Decimal
    line_subtotal: Decimal
    line_tax: Decimal
    line_total: Decimal


class CreditNoteRepository:
    """Acceso a notas crédito y sus líneas."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def create_draft(
        self,
        *,
        invoice_id: UUID,
        issue_date: date,
        lines: list[NewCreditNoteLine],
        subtotal: Decimal,
        tax_total: Decimal,
        total: Decimal,
    ) -> CreditNote:
        """Crea una nota crédito DRAFT con sus líneas, sin número."""
        credit_note = CreditNote(
            number=None,
            invoice_id=invoice_id,
            issue_date=issue_date,
            status=CreditNoteStatus.DRAFT,
            subtotal=subtotal,
            tax_total=tax_total,
            total=total,
        )
        credit_note.lines = [
            CreditNoteLine(
                invoice_line_id=line.invoice_line_id,
                description=line.description,
                quantity=line.quantity,
                unit_price=line.unit_price,
                tax_rate=line.tax_rate,
                line_subtotal=line.line_subtotal,
                line_tax=line.line_tax,
                line_total=line.line_total,
            )
            for line in lines
        ]
        self.db.add(credit_note)
        self.db.flush()
        self.db.refresh(credit_note)
        return credit_note

    def get_by_id(self, credit_note_id: UUID) -> CreditNote | None:
        statement = (
            select(CreditNote)
            .where(CreditNote.id == credit_note_id)
            .options(selectinload(CreditNote.lines))
        )
        return self.db.scalar(statement)

    def list_by_invoice(
        self,
        invoice_id: UUID,
        limit: int,
        offset: int,
    ) -> list[CreditNote]:
        """Lista notas crédito de una factura."""
        statement = (
            select(CreditNote)
            .where(CreditNote.invoice_id == invoice_id)
            .options(selectinload(CreditNote.lines))
            .order_by(CreditNote.created_at.desc(), CreditNote.id)
            .limit(limit)
            .offset(offset)
        )
        return list(self.db.scalars(statement).all())

    def issue(self, credit_note_id: UUID) -> CreditNote:
        """Emite una nota crédito DRAFT y asigna el siguiente número."""
        credit_note = self.db.scalar(
            select(CreditNote).where(CreditNote.id == credit_note_id).with_for_update()
        )
        if credit_note is None:
            raise ResourceNotFoundError("Nota crédito no encontrada")
        if credit_note.status is not CreditNoteStatus.DRAFT:
            from app.domain.exceptions import InvoiceStateError

            raise InvoiceStateError("Solo se emiten notas crédito en estado borrador")

        sequence = self.db.scalar(
            select(NumberSequence)
            .where(NumberSequence.name == CREDIT_NOTE_SEQUENCE_NAME)
            .with_for_update()
        )
        if sequence is None:
            self.db.execute(
                pg_insert(NumberSequence)
                .values(
                    name=CREDIT_NOTE_SEQUENCE_NAME,
                    prefix=CREDIT_NOTE_SEQUENCE_PREFIX,
                    next_number=1,
                )
                .on_conflict_do_nothing(index_elements=["name"])
            )
            sequence = self.db.scalar(
                select(NumberSequence)
                .where(NumberSequence.name == CREDIT_NOTE_SEQUENCE_NAME)
                .with_for_update()
            )
            if sequence is None:
                raise RuntimeError("No se pudo crear la secuencia de notas crédito")

        credit_note.number = f"{sequence.prefix}{sequence.next_number:08d}"
        sequence.next_number += 1
        credit_note.status = CreditNoteStatus.ISSUED
        credit_note.version += 1
        credit_note.updated_at = datetime.now(UTC)

        self.db.flush()
        return credit_note

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
