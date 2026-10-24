"""Repositorio de facturas de compra con SQLAlchemy 2."""

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
from app.domain.models.idempotency_key import IdempotencyKey
from app.domain.models.number_sequence import NumberSequence
from app.domain.models.purchase import PurchaseInvoice, PurchaseLine, PurchaseStatus

PURCHASE_SEQUENCE_NAME = "purchase"
PURCHASE_SEQUENCE_PREFIX = "FC"


@dataclass(frozen=True)
class NewPurchaseLine:
    """Línea ya calculada y lista para persistir."""

    item_id: UUID | None
    description: str
    quantity: Decimal
    unit_cost: Decimal
    tax_rate: Decimal
    line_subtotal: Decimal
    line_tax: Decimal
    line_total: Decimal


class PurchaseRepository:
    """Acceso a facturas de compra y sus líneas."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def create_draft(
        self,
        *,
        supplier_id: UUID,
        issue_date: date,
        due_date: date,
        lines: list[NewPurchaseLine],
        subtotal: Decimal,
        tax_total: Decimal,
        total: Decimal,
    ) -> PurchaseInvoice:
        """Crea una factura de compra DRAFT con sus líneas, sin número."""
        purchase = PurchaseInvoice(
            number=None,
            supplier_id=supplier_id,
            issue_date=issue_date,
            due_date=due_date,
            status=PurchaseStatus.DRAFT,
            subtotal=subtotal,
            tax_total=tax_total,
            total=total,
            balance=total,
        )
        purchase.lines = [
            PurchaseLine(
                item_id=line.item_id,
                description=line.description,
                quantity=line.quantity,
                unit_cost=line.unit_cost,
                tax_rate=line.tax_rate,
                line_subtotal=line.line_subtotal,
                line_tax=line.line_tax,
                line_total=line.line_total,
            )
            for line in lines
        ]
        self.db.add(purchase)
        self.db.flush()
        self.db.refresh(purchase)
        return purchase

    def get_by_id(self, purchase_id: UUID) -> PurchaseInvoice | None:
        statement = (
            select(PurchaseInvoice)
            .where(PurchaseInvoice.id == purchase_id)
            .options(selectinload(PurchaseInvoice.lines))
        )
        return self.db.scalar(statement)

    def list(self, limit: int, offset: int) -> list[PurchaseInvoice]:
        """Lista facturas de compra ordenadas por fecha de creación."""
        statement = (
            select(PurchaseInvoice)
            .options(selectinload(PurchaseInvoice.lines))
            .order_by(PurchaseInvoice.created_at.desc(), PurchaseInvoice.id)
            .limit(limit)
            .offset(offset)
        )
        return list(self.db.scalars(statement).all())

    def issue(self, purchase_id: UUID) -> PurchaseInvoice:
        """Emite una factura de compra DRAFT y asigna el siguiente número.

        Genera el número secuencial con prefijo FC y bloquea la fila para
        evitar emisiones concurrentes.
        """
        purchase = self.db.scalar(
            select(PurchaseInvoice).where(PurchaseInvoice.id == purchase_id).with_for_update()
        )
        if purchase is None:
            raise ResourceNotFoundError("Factura de compra no encontrada")
        if purchase.status is not PurchaseStatus.DRAFT:
            from app.domain.exceptions import InvoiceStateError

            raise InvoiceStateError("Solo se emiten facturas de compra en estado borrador")

        sequence = self.db.scalar(
            select(NumberSequence)
            .where(NumberSequence.name == PURCHASE_SEQUENCE_NAME)
            .with_for_update()
        )
        if sequence is None:
            self.db.execute(
                pg_insert(NumberSequence)
                .values(
                    name=PURCHASE_SEQUENCE_NAME,
                    prefix=PURCHASE_SEQUENCE_PREFIX,
                    next_number=1,
                )
                .on_conflict_do_nothing(index_elements=["name"])
            )
            sequence = self.db.scalar(
                select(NumberSequence)
                .where(NumberSequence.name == PURCHASE_SEQUENCE_NAME)
                .with_for_update()
            )
            if sequence is None:
                raise RuntimeError("No se pudo crear la secuencia de compras")

        purchase.number = f"{sequence.prefix}{sequence.next_number:08d}"
        sequence.next_number += 1
        purchase.status = PurchaseStatus.ISSUED
        purchase.version += 1
        purchase.updated_at = datetime.now(UTC)

        self.db.flush()
        return purchase

    def void_purchase(self, purchase_id: UUID, reason: str) -> PurchaseInvoice:
        """Anula una factura de compra emitida sin contra-asiento (Fase MVP)."""
        purchase = self.db.scalar(
            select(PurchaseInvoice).where(PurchaseInvoice.id == purchase_id).with_for_update()
        )
        if purchase is None:
            raise ResourceNotFoundError("Factura de compra no encontrada")
        if purchase.status is PurchaseStatus.DRAFT:
            from app.domain.exceptions import InvoiceStateError

            raise InvoiceStateError("No se puede anular un borrador, elimínelo")
        if purchase.status is PurchaseStatus.VOID:
            from app.domain.exceptions import InvoiceStateError

            raise InvoiceStateError("Factura de compra ya anulada")

        now = datetime.now(UTC)
        purchase.status = PurchaseStatus.VOID
        purchase.version += 1
        purchase.updated_at = now
        self.db.flush()
        return purchase

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
