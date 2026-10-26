"""Acuerdos de pago: renegociación formal de cartera.

Los acuerdos son instrumentos **de gestión**, no contables. No generan
asientos ni modifican el saldo de la factura: el pago real registrado con
``PaymentService`` es el único hecho que contabiliza. Esto evita duplicar
ingresos en la contabilidad.

Las cuotas se generan con ``Decimal`` y la última absorbe el redondeo para
que la suma sea exactamente ``total_amount``.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import ROUND_DOWN, Decimal
from uuid import UUID

from sqlalchemy.orm import Session

from app.domain.calculations import round_money
from app.domain.exceptions import (
    AgreementError,
    AgreementValidationError,
    ResourceNotFoundError,
)
from app.domain.models.invoice import LifecycleStatus
from app.domain.models.receivables import (
    AgreementStatus,
    PaymentAgreement,
    PaymentAgreementInstallment,
)
from app.domain.receivables_repository import ReceivablesRepository

ZERO = Decimal("0.00")
CENT = Decimal("0.01")


def split_installments(total_amount: Decimal, installments: int) -> list[Decimal]:
    """Reparte ``total_amount`` en cuotas que suman exactamente el total.

    Las primeras ``n - 1`` cuotas usan división truncada a centavos y la
    última absorbe el remanente. Ejemplo: ``1.000.000 / 3`` produce
    ``333.333,33 + 333.333,33 + 333.333,34``.
    """
    if installments < 1:
        raise AgreementValidationError("El acuerdo debe tener al menos una cuota")
    if total_amount <= ZERO:
        raise AgreementValidationError("El monto total debe ser mayor que cero")

    base = (total_amount / installments).quantize(CENT, rounding=ROUND_DOWN)
    amounts = [base for _ in range(installments - 1)]
    amounts.append(round_money(total_amount - (base * (installments - 1))))
    return amounts


class AgreementService:
    """Ciclo de vida de acuerdos de pago y sus cuotas."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.repository = ReceivablesRepository(db)

    def create(
        self,
        *,
        contact_id: UUID,
        invoice_id: UUID | None,
        total_amount: Decimal,
        installments: int,
        start_date: date,
        frequency_days: int = 30,
        notes: str | None = None,
        created_by: UUID,
    ) -> PaymentAgreement:
        """Crea el acuerdo y genera automáticamente sus cuotas."""
        if self.repository.get_contact(contact_id) is None:
            raise ResourceNotFoundError("Contacto no encontrado")
        if installments < 1:
            raise AgreementValidationError("El número de cuotas debe ser al menos 1")
        if frequency_days < 1:
            raise AgreementValidationError("La frecuencia debe ser al menos 1 día")
        if total_amount <= ZERO:
            raise AgreementValidationError("El monto total debe ser mayor que cero")

        if invoice_id is not None:
            invoice = self.repository.get_invoice(invoice_id)
            if invoice is None:
                raise ResourceNotFoundError("Factura no encontrada")
            if invoice.contact_id != contact_id:
                raise AgreementValidationError("La factura no pertenece al contacto")
            if invoice.lifecycle_status is not LifecycleStatus.ISSUED:
                raise AgreementValidationError("Solo se pueden acordar facturas emitidas")
            outstanding = self.repository.outstanding_for_invoice(invoice)
            if total_amount > outstanding:
                raise AgreementValidationError(
                    "El monto del acuerdo supera el saldo pendiente de la factura"
                )

        amounts = split_installments(total_amount, installments)
        installment_items = [
            PaymentAgreementInstallment(
                due_date=start_date + timedelta(days=index * frequency_days),
                amount=amount,
                paid_amount=ZERO,
            )
            for index, amount in enumerate(amounts)
        ]

        agreement = self.repository.create_agreement(
            values={
                "contact_id": contact_id,
                "invoice_id": invoice_id,
                "total_amount": total_amount,
                "installments": installments,
                "start_date": start_date,
                "status": AgreementStatus.ACTIVE,
                "notes": notes,
                "created_by": created_by,
            },
            installments=installment_items,
        )
        return self.get(agreement.id)

    def get(self, agreement_id: UUID) -> PaymentAgreement:
        agreement = self.repository.get_agreement(agreement_id)
        if agreement is None:
            raise ResourceNotFoundError("Acuerdo de pago no encontrado")
        return agreement

    def list(
        self,
        *,
        contact_id: UUID | None = None,
        status: AgreementStatus | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[PaymentAgreement]:
        return self.repository.list_agreements(
            contact_id=contact_id,
            status=status,
            limit=limit,
            offset=offset,
        )

    def register_installment_payment(
        self,
        *,
        agreement_id: UUID,
        installment_id: UUID,
        amount: Decimal,
        paid_by: UUID,
    ) -> PaymentAgreement:
        """Registra un abono a una cuota; nunca supera el valor de la cuota.

        ``paid_by`` identifica al usuario que registra la gestión. No crea
        contabilidad: el pago real se registra con ``PaymentService``.
        """
        del paid_by  # Se conserva en la firma para trazabilidad futura.
        if amount <= ZERO:
            raise AgreementValidationError("El abono debe ser mayor que cero")

        agreement = self.repository.get_agreement_for_update(agreement_id)
        if agreement is None:
            raise ResourceNotFoundError("Acuerdo de pago no encontrado")
        if agreement.status is not AgreementStatus.ACTIVE:
            raise AgreementError("Solo se abonan cuotas de acuerdos activos")

        installment = self.repository.get_installment_for_update(
            agreement_id=agreement_id,
            installment_id=installment_id,
        )
        if installment is None:
            raise ResourceNotFoundError("Cuota no encontrada")

        remaining = installment.amount - installment.paid_amount
        if amount > remaining:
            raise AgreementValidationError("El abono supera el saldo pendiente de la cuota")

        installment.paid_amount = round_money(installment.paid_amount + amount)
        if installment.paid_amount >= installment.amount:
            installment.paid_amount = installment.amount
            installment.paid_at = datetime.now(UTC)

        self._refresh_status(agreement)
        self.db.flush()
        return self.get(agreement_id)

    def cancel(self, agreement_id: UUID) -> PaymentAgreement:
        """Cancela el acuerdo sin tocar los abonos ya registrados."""
        agreement = self.get(agreement_id)
        if agreement.status is AgreementStatus.COMPLETED:
            raise AgreementError("No se puede cancelar un acuerdo ya completado")
        agreement.status = AgreementStatus.CANCELLED
        self.db.flush()
        return agreement

    def mark_broken(self, agreement_id: UUID) -> PaymentAgreement:
        """Marca como incumplido un acuerdo activo con cuotas vencidas."""
        agreement = self.get(agreement_id)
        if agreement.status is not AgreementStatus.ACTIVE:
            raise AgreementError("Solo se pueden marcar como incumplidos acuerdos activos")
        agreement.status = AgreementStatus.BROKEN
        self.db.flush()
        return agreement

    def _refresh_status(self, agreement: PaymentAgreement) -> None:
        """Completa el acuerdo cuando todas las cuotas quedan pagadas."""
        if agreement.installment_items and all(
            item.paid_amount >= item.amount for item in agreement.installment_items
        ):
            agreement.status = AgreementStatus.COMPLETED


__all__ = ["AgreementService", "split_installments"]
