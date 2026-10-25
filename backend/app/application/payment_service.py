"""Caso de uso compartido para registrar un pago sobre una factura."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.application.accounting.service import AccountingService
from app.domain.models.invoice import Invoice
from app.domain.models.payment import Payment
from app.domain.payment_repository import PaymentRepository


class PaymentService:
    """Crea el pago, recalcula la factura y genera su asiento.

    No valida estado ni sobrepago y no hace commit: el endpoint que conoce la
    idempotencia y el lock de la factura conserva esas responsabilidades. El
    POS reutiliza este mismo flujo después de emitir la factura.
    """

    def __init__(self, db: Session) -> None:
        self.repository = PaymentRepository(db)
        self.accounting = AccountingService(db)

    def register_payment(
        self,
        *,
        invoice: Invoice,
        amount: Decimal,
        payment_date: date,
        method: str,
        reference: str | None = None,
    ) -> Payment:
        """Registra el pago y deja la factura y la contabilidad actualizadas."""
        payment = self.repository.create_payment(
            invoice_id=invoice.id,
            amount=amount,
            payment_date=payment_date,
            method=method,
            reference=reference,
        )
        self.repository.recalculate_invoice(invoice)
        self.accounting.record_payment(payment, invoice)
        return payment
