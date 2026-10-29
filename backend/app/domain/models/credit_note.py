"""Modelo de notas crédito para facturas de venta."""

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
    Integer,
    Numeric,
    String,
    Text,
    Uuid,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.domain.models.tenancy import CompanyScopedMixin
from app.infrastructure.database import Base

if TYPE_CHECKING:
    from app.domain.models.invoice import Invoice


class CreditNoteStatus(enum.StrEnum):
    DRAFT = "draft"
    ISSUED = "issued"


def _enum_values(enum_cls: type[enum.StrEnum]) -> list[str]:
    """Persiste los valores, no los nombres, de los enums."""
    return [member.value for member in enum_cls]


class CreditNote(CompanyScopedMixin, Base):
    """Nota crédito asociada a una factura de venta emitida."""

    __tablename__ = "credit_notes"

    __table_args__ = (
        CheckConstraint("subtotal >= 0", name="ck_credit_notes_subtotal_non_negative"),
        CheckConstraint("tax_total >= 0", name="ck_credit_notes_tax_total_non_negative"),
        CheckConstraint("total >= 0", name="ck_credit_notes_total_non_negative"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    invoice_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("invoices.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    number: Mapped[str | None] = mapped_column(String(50))
    issue_date: Mapped[date | None] = mapped_column(Date, index=True)

    status: Mapped[CreditNoteStatus] = mapped_column(
        Enum(
            CreditNoteStatus,
            name="credit_note_status",
            native_enum=True,
            values_callable=_enum_values,
        ),
        nullable=False,
        default=CreditNoteStatus.DRAFT,
        server_default=text("'draft'"),
        index=True,
    )

    subtotal: Mapped[Decimal] = mapped_column(
        Numeric(18, 2), nullable=False, server_default=text("0")
    )
    tax_total: Mapped[Decimal] = mapped_column(
        Numeric(18, 2), nullable=False, server_default=text("0")
    )
    total: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, server_default=text("0"))

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

    invoice: Mapped[Invoice] = relationship(back_populates="credit_notes")
    lines: Mapped[list[CreditNoteLine]] = relationship(
        back_populates="credit_note",
        cascade="all, delete-orphan",
        order_by="CreditNoteLine.id",
    )


class CreditNoteLine(CompanyScopedMixin, Base):
    """Línea de una nota crédito."""

    __tablename__ = "credit_note_lines"

    __table_args__ = (
        CheckConstraint("quantity > 0", name="ck_credit_note_lines_quantity_positive"),
        CheckConstraint("unit_price >= 0", name="ck_credit_note_lines_unit_price_non_negative"),
        CheckConstraint(
            "tax_rate >= 0 AND tax_rate <= 100",
            name="ck_credit_note_lines_tax_rate_range",
        ),
        CheckConstraint(
            "line_subtotal >= 0",
            name="ck_credit_note_lines_subtotal_non_negative",
        ),
        CheckConstraint("line_tax >= 0", name="ck_credit_note_lines_tax_non_negative"),
        CheckConstraint("line_total >= 0", name="ck_credit_note_lines_total_non_negative"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    credit_note_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("credit_notes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    invoice_line_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("invoice_lines.id", ondelete="RESTRICT"),
        index=True,
    )
    description: Mapped[str] = mapped_column(Text, nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    tax_rate: Mapped[Decimal] = mapped_column(
        Numeric(7, 4), nullable=False, server_default=text("0")
    )
    line_subtotal: Mapped[Decimal] = mapped_column(
        Numeric(18, 2), nullable=False, server_default=text("0")
    )
    line_tax: Mapped[Decimal] = mapped_column(
        Numeric(18, 2), nullable=False, server_default=text("0")
    )
    line_total: Mapped[Decimal] = mapped_column(
        Numeric(18, 2), nullable=False, server_default=text("0")
    )

    credit_note: Mapped[CreditNote] = relationship(back_populates="lines")
