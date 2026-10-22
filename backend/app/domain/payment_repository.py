"""Repositorio de pagos con SQLAlchemy 2."""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.domain.calculations import payment_status_for_balance, round_money
from app.domain.models.idempotency_key import IdempotencyKey
from app.domain.models.invoice import Invoice
from app.domain.models.payment import Payment


class PaymentRepository:
    """Acceso a pagos y a la factura que actualizan.

    Ningún método hace commit: la transacción completa (pago + factura +
    idempotencia) la controla la capa de API.
    """

    def __init__(self, db: Session) -> None:
        self.db = db

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

    def get_invoice(self, invoice_id: UUID) -> Invoice | None:
        """Obtiene una factura no eliminada, sin bloquearla."""
        return self.db.scalar(
            select(Invoice).where(Invoice.id == invoice_id, Invoice.deleted_at.is_(None))
        )

    def get_invoice_for_update(self, invoice_id: UUID) -> Invoice | None:
        """Bloquea una factura no eliminada para serializar pagos concurrentes."""
        return self.db.scalar(
            select(Invoice)
            .where(Invoice.id == invoice_id, Invoice.deleted_at.is_(None))
            .with_for_update()
        )

    def create_payment(
        self,
        *,
        invoice_id: UUID,
        amount: Decimal,
        payment_date: date,
        method: str,
        reference: str | None,
    ) -> Payment:
        """Inserta el pago y lo deja visible para la suma de la transacción."""
        payment = Payment(
            invoice_id=invoice_id,
            amount=amount,
            payment_date=payment_date,
            method=method,
            reference=reference,
        )
        self.db.add(payment)
        self.db.flush()
        self.db.refresh(payment)
        return payment

    def total_paid(self, invoice_id: UUID) -> Decimal:
        """Suma real de los pagos registrados para una factura."""
        value = self.db.scalar(
            select(func.coalesce(func.sum(Payment.amount), Decimal("0.00"))).where(
                Payment.invoice_id == invoice_id
            )
        )
        if value is None:
            return Decimal("0.00")
        return round_money(value)

    def current_balance(self, invoice: Invoice) -> Decimal:
        """Recalcula el saldo desde la suma real de pagos."""
        return round_money(invoice.total - self.total_paid(invoice.id))

    def recalculate_invoice(self, invoice: Invoice) -> None:
        """Actualiza saldo, estado de pago, versión y fecha de la factura."""
        invoice.balance = self.current_balance(invoice)
        invoice.payment_status = payment_status_for_balance(
            total=invoice.total,
            balance=invoice.balance,
        )
        invoice.version += 1
        invoice.updated_at = datetime.now(UTC)

    def list_payments(self, invoice_id: UUID, *, limit: int, offset: int) -> list[Payment]:
        """Lista pagos por fecha descendente, con desempate estable por id."""
        statement = (
            select(Payment)
            .where(Payment.invoice_id == invoice_id)
            .order_by(Payment.payment_date.desc(), Payment.id.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(self.db.scalars(statement).all())

    def get_payment_for_update(self, invoice_id: UUID, payment_id: UUID) -> Payment | None:
        """Busca y bloquea un pago que pertenezca a la factura indicada."""
        return self.db.scalar(
            select(Payment)
            .where(Payment.id == payment_id, Payment.invoice_id == invoice_id)
            .with_for_update()
        )

    def delete_payment(self, payment: Payment) -> None:
        """Elimina físicamente el pago; los pagos son transacciones, no catálogos."""
        self.db.delete(payment)
        self.db.flush()
