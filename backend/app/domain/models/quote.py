"""Modelo de cotizaciones de venta (pre-ventas / CRM)."""

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
    UniqueConstraint,
    Uuid,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.domain.models.tenancy import CompanyScopedMixin
from app.infrastructure.database import Base

if TYPE_CHECKING:
    from app.domain.models.contact import Contact
    from app.domain.models.invoice import Invoice
    from app.domain.models.quote_line import QuoteLine


def _enum_values(enum_cls: type[enum.StrEnum]) -> list[str]:
    """Persiste los valores, no los nombres, de los enums."""
    return [member.value for member in enum_cls]


class QuoteStatus(enum.StrEnum):
    DRAFT = "DRAFT"
    SENT = "SENT"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    CONVERTED = "CONVERTED"


class Quote(CompanyScopedMixin, Base):
    __tablename__ = "quotes"

    __table_args__ = (
        UniqueConstraint("company_id", "number", name="uq_quotes_company_number"),
        CheckConstraint("subtotal >= 0", name="ck_quotes_subtotal_non_negative"),
        CheckConstraint("tax_total >= 0", name="ck_quotes_tax_total_non_negative"),
        CheckConstraint("total >= 0", name="ck_quotes_total_non_negative"),
        CheckConstraint(
            "expiry_date IS NULL OR issue_date IS NULL OR expiry_date >= issue_date",
            name="ck_quotes_expiry_date_after_issue_date",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    # -- REQUIERE VALIDACIÓN: contador/experto DIAN (numeración de cotizaciones).
    number: Mapped[str | None] = mapped_column(
        String(50),
        comment=("REQUIERE VALIDACIÓN: contador/experto DIAN. Numeración de cotizaciones."),
    )
    contact_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("contacts.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    # -- REQUIERE VALIDACIÓN: contador/experto DIAN (reglas de fecha de emisión).
    issue_date: Mapped[date | None] = mapped_column(
        Date,
        index=True,
        comment=("REQUIERE VALIDACIÓN: contador/experto DIAN. Reglas de fecha de emisión."),
    )
    expiry_date: Mapped[date | None] = mapped_column(
        Date,
        comment=(
            "REQUIERE VALIDACIÓN: contador/experto DIAN. Fecha de vencimiento de la cotización."
        ),
    )

    status: Mapped[QuoteStatus] = mapped_column(
        Enum(
            QuoteStatus,
            name="quote_status",
            native_enum=True,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
        default=QuoteStatus.DRAFT,
        server_default=text("'DRAFT'"),
        index=True,
    )

    # Factura generada al convertir la cotización (nullable hasta convertir).
    converted_invoice_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("invoices.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )

    # Soft delete.
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Monto calculados.
    subtotal: Mapped[Decimal] = mapped_column(
        Numeric(18, 2), nullable=False, server_default=text("0")
    )
    tax_total: Mapped[Decimal] = mapped_column(
        Numeric(18, 2), nullable=False, server_default=text("0")
    )
    total: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, server_default=text("0"))
    # MVP solo COP.
    currency: Mapped[str] = mapped_column(
        String(3),
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

    contact: Mapped[Contact] = relationship(back_populates="quotes")
    converted_invoice: Mapped[Invoice | None] = relationship(foreign_keys=[converted_invoice_id])
    lines: Mapped[list[QuoteLine]] = relationship(
        back_populates="quote",
        cascade="all, delete-orphan",
        order_by="QuoteLine.id",
    )

    @property
    def converted_invoice_number(self) -> str | None:
        """Número legible de la factura generada al convertir la cotización."""
        if self.converted_invoice is None:
            return None
        return self.converted_invoice.number


__all__ = ["Quote", "QuoteStatus"]
