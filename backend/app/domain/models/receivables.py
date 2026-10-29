"""Modelos de cartera: recordatorios de cobranza y acuerdos de pago.

Los acuerdos de pago son instrumentos **de gestión**, no contables: no
generan asientos ni modifican el saldo de la factura. El pago real
(``payments``) es el único hecho económico que contabiliza el sistema.

El aging y los saldos son valores derivados: se calculan en lectura a partir
de facturas, pagos y notas crédito, y nunca se persisten en estas tablas.
"""

from __future__ import annotations

import enum
import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    Text,
    Uuid,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.domain.models.tenancy import CompanyScopedMixin
from app.infrastructure.database import Base

if TYPE_CHECKING:
    from app.domain.models.auth import User
    from app.domain.models.contact import Contact
    from app.domain.models.invoice import Invoice


class ReminderChannel(enum.StrEnum):
    """Canal del recordatorio de cobranza.

    Hoy solo ``IN_APP`` tiene implementación funcional; los demás canales
    quedan reservados para integraciones futuras.
    """

    IN_APP = "IN_APP"
    EMAIL = "EMAIL"
    SMS = "SMS"
    CALL = "CALL"


class AgreementStatus(enum.StrEnum):
    """Ciclo de vida de un acuerdo de pago."""

    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    BROKEN = "BROKEN"
    CANCELLED = "CANCELLED"


def _enum_values(enum_cls: type[enum.StrEnum]) -> list[str]:
    """Persiste los valores, no los nombres, de los enums."""
    return [member.value for member in enum_cls]


class PaymentReminder(CompanyScopedMixin, Base):
    """Recordatorio de cobranza enviado (o registrado) sobre una factura.

    ``contact_id`` se duplica desde la factura para permitir consultas de
    aging e historial por cliente sin un JOIN adicional.
    """

    __tablename__ = "payment_reminders"

    __table_args__ = (
        CheckConstraint("level BETWEEN 1 AND 5", name="ck_payment_reminders_level_range"),
        Index("ix_payment_reminders_invoice_sent", "invoice_id", "sent_at"),
        Index("ix_payment_reminders_contact_id", "contact_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    invoice_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("invoices.id", ondelete="CASCADE"),
        nullable=False,
    )
    contact_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("contacts.id", ondelete="RESTRICT"),
        nullable=False,
    )
    level: Mapped[int] = mapped_column(Integer, nullable=False)
    channel: Mapped[ReminderChannel] = mapped_column(
        Enum(
            ReminderChannel,
            name="payment_reminder_channel",
            native_enum=True,
            values_callable=_enum_values,
        ),
        nullable=False,
        default=ReminderChannel.IN_APP,
        server_default=text("'IN_APP'"),
    )
    sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    invoice: Mapped[Invoice] = relationship()
    contact: Mapped[Contact] = relationship()
    creator: Mapped[User] = relationship()


class PaymentAgreement(CompanyScopedMixin, Base):
    """Acuerdo de pago (global del cliente o ligado a una factura)."""

    __tablename__ = "payment_agreements"

    __table_args__ = (
        CheckConstraint("total_amount >= 0", name="ck_payment_agreements_total_non_negative"),
        CheckConstraint("installments >= 1", name="ck_payment_agreements_installments_positive"),
        Index("ix_payment_agreements_contact_status", "contact_id", "status"),
        Index("ix_payment_agreements_invoice_id", "invoice_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    contact_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("contacts.id", ondelete="RESTRICT"),
        nullable=False,
    )
    invoice_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("invoices.id", ondelete="RESTRICT"),
        nullable=True,
    )
    total_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    installments: Mapped[int] = mapped_column(Integer, nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[AgreementStatus] = mapped_column(
        Enum(
            AgreementStatus,
            name="payment_agreement_status",
            native_enum=True,
            values_callable=_enum_values,
        ),
        nullable=False,
        default=AgreementStatus.ACTIVE,
        server_default=text("'ACTIVE'"),
        index=True,
    )
    notes: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    contact: Mapped[Contact] = relationship()
    invoice: Mapped[Invoice | None] = relationship()
    creator: Mapped[User] = relationship()
    installment_items: Mapped[list[PaymentAgreementInstallment]] = relationship(
        back_populates="agreement",
        cascade="all, delete-orphan",
        order_by="PaymentAgreementInstallment.due_date",
    )

    @property
    def paid_total(self) -> Decimal:
        """Suma de lo pagado en las cuotas (derivado, no persistido)."""
        return sum((item.paid_amount for item in self.installment_items), Decimal("0.00"))

    @property
    def balance(self) -> Decimal:
        """Saldo pendiente del acuerdo (derivado, no persistido)."""
        return self.total_amount - self.paid_total


class PaymentAgreementInstallment(CompanyScopedMixin, Base):
    """Cuota de un acuerdo de pago."""

    __tablename__ = "payment_agreement_installments"

    __table_args__ = (
        CheckConstraint("amount >= 0", name="ck_agreement_installments_amount_non_negative"),
        CheckConstraint("paid_amount >= 0", name="ck_agreement_installments_paid_non_negative"),
        Index("ix_payment_agreement_installments_agreement_id", "agreement_id"),
        Index("ix_payment_agreement_installments_due_date", "due_date"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    agreement_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("payment_agreements.id", ondelete="CASCADE"),
        nullable=False,
    )
    due_date: Mapped[date] = mapped_column(Date, nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    paid_amount: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        nullable=False,
        default=Decimal("0.00"),
        server_default=text("0"),
    )
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    agreement: Mapped[PaymentAgreement] = relationship(back_populates="installment_items")

    @property
    def balance(self) -> Decimal:
        """Saldo de la cuota (derivado)."""
        return self.amount - self.paid_amount


__all__ = [
    "AgreementStatus",
    "PaymentAgreement",
    "PaymentAgreementInstallment",
    "PaymentReminder",
    "ReminderChannel",
]
