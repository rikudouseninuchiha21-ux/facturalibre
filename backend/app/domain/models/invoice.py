"""Modelo de facturas de venta."""

from __future__ import annotations

import enum
import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    CHAR,
    CheckConstraint,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    Uuid,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.database import Base

if TYPE_CHECKING:
    from app.domain.models.contact import Contact
    from app.domain.models.invoice_line import InvoiceLine
    from app.domain.models.payment import Payment


class LifecycleStatus(enum.StrEnum):
    DRAFT = "draft"
    ISSUED = "issued"
    VOID = "void"


class PaymentStatus(enum.StrEnum):
    UNPAID = "unpaid"
    PARTIALLY_PAID = "partially_paid"
    PAID = "paid"
    OVERPAID = "overpaid"


class Invoice(Base):
    __tablename__ = "invoices"

    __table_args__ = (
        UniqueConstraint("number", name="uq_invoices_number"),
        CheckConstraint("subtotal >= 0", name="ck_invoices_subtotal_non_negative"),
        CheckConstraint("tax_total >= 0", name="ck_invoices_tax_total_non_negative"),
        CheckConstraint("total >= 0", name="ck_invoices_total_non_negative"),
        CheckConstraint("balance >= 0", name="ck_invoices_balance_non_negative"),
        CheckConstraint("currency = 'COP'", name="ck_invoices_currency_cop"),
        CheckConstraint(
            "due_date IS NULL OR issue_date IS NULL OR due_date >= issue_date",
            name="ck_invoices_due_date_after_issue_date",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    # -- REQUIERE VALIDACIÓN: contador/experto DIAN (numeración autorizada, prefijo y rango).
    number: Mapped[str | None] = mapped_column(
        String(50),
        comment=(
            "REQUIERE VALIDACIÓN: contador/experto DIAN. Numeración autorizada, prefijo y rango."
        ),
    )
    contact_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("contacts.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    # -- REQUIERE VALIDACIÓN: contador/experto DIAN (reglas de fecha de emisión).
    issue_date: Mapped[date | None] = mapped_column(
        Date,
        index=True,
        comment=("REQUIERE VALIDACIÓN: contador/experto DIAN. Reglas de fecha de emisión."),
    )
    due_date: Mapped[date | None] = mapped_column(Date)

    # DECISIONES.md: dos dimensiones separadas, nunca un único "status".
    lifecycle_status: Mapped[LifecycleStatus] = mapped_column(
        Enum(
            LifecycleStatus,
            name="invoice_lifecycle_status",
            native_enum=True,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
        default=LifecycleStatus.DRAFT,
        server_default=text("'draft'"),
        index=True,
    )
    # Derivado de pagos y notas crédito; no debe escribirse desde la API.
    payment_status: Mapped[PaymentStatus] = mapped_column(
        Enum(
            PaymentStatus,
            name="invoice_payment_status",
            native_enum=True,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
        default=PaymentStatus.UNPAID,
        server_default=text("'unpaid'"),
        index=True,
    )

    # Solo se llenan cuando la factura se anula.
    voided_reason: Mapped[str | None] = mapped_column(String(500))
    voided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Soft delete: las facturas borradas no se devuelven por la API.
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    subtotal: Mapped[Decimal] = mapped_column(
        Numeric(18, 2), nullable=False, server_default=text("0")
    )
    tax_total: Mapped[Decimal] = mapped_column(
        Numeric(18, 2), nullable=False, server_default=text("0")
    )
    total: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, server_default=text("0"))
    balance: Mapped[Decimal] = mapped_column(
        Numeric(18, 2), nullable=False, server_default=text("0")
    )
    # MVP solo COP; la columna queda preparada para Fase2.
    currency: Mapped[str] = mapped_column(
        CHAR(3),
        nullable=False,
        server_default=text("'COP'"),
        comment=("MVP solo COP. REQUIERE VALIDACIÓN: contador/experto DIAN para multimoneda."),
    )

    # DECISIONES.md: optimistic locking.
    version: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1, server_default=text("1")
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

    contact: Mapped[Contact] = relationship(back_populates="invoices")
    lines: Mapped[list[InvoiceLine]] = relationship(
        back_populates="invoice",
        cascade="all, delete-orphan",
        order_by="InvoiceLine.id",
    )
    payments: Mapped[list[Payment]] = relationship(back_populates="invoice")
