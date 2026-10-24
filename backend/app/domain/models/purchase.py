"""Modelo de facturas de compra (proveedores)."""

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

from app.infrastructure.database import Base

if TYPE_CHECKING:
    from app.domain.models.contact import Contact
    from app.domain.models.item import Item


class PurchaseStatus(enum.StrEnum):
    DRAFT = "draft"
    ISSUED = "issued"
    VOID = "void"


def _enum_values(enum_cls: type[enum.StrEnum]) -> list[str]:
    """Persiste los valores, no los nombres, de los enums."""
    return [member.value for member in enum_cls]


class PurchaseInvoice(Base):
    """Factura de compra recibida de un proveedor."""

    __tablename__ = "purchase_invoices"

    __table_args__ = (
        CheckConstraint("subtotal >= 0", name="ck_purchase_invoices_subtotal_non_negative"),
        CheckConstraint("tax_total >= 0", name="ck_purchase_invoices_tax_total_non_negative"),
        CheckConstraint("total >= 0", name="ck_purchase_invoices_total_non_negative"),
        CheckConstraint("balance >= 0", name="ck_purchase_invoices_balance_non_negative"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    supplier_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("contacts.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    number: Mapped[str | None] = mapped_column(String(50))
    issue_date: Mapped[date | None] = mapped_column(Date, index=True)
    due_date: Mapped[date | None] = mapped_column(Date)

    status: Mapped[PurchaseStatus] = mapped_column(
        Enum(
            PurchaseStatus,
            name="purchase_invoice_status",
            native_enum=True,
            values_callable=_enum_values,
        ),
        nullable=False,
        default=PurchaseStatus.DRAFT,
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
    balance: Mapped[Decimal] = mapped_column(
        Numeric(18, 2), nullable=False, server_default=text("0")
    )

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

    supplier: Mapped[Contact] = relationship(back_populates="purchase_invoices")
    lines: Mapped[list[PurchaseLine]] = relationship(
        back_populates="purchase_invoice",
        cascade="all, delete-orphan",
        order_by="PurchaseLine.id",
    )


class PurchaseLine(Base):
    """Línea de una factura de compra."""

    __tablename__ = "purchase_lines"

    __table_args__ = (
        CheckConstraint("quantity > 0", name="ck_purchase_lines_quantity_positive"),
        CheckConstraint("unit_cost >= 0", name="ck_purchase_lines_unit_cost_non_negative"),
        CheckConstraint(
            "tax_rate >= 0 AND tax_rate <= 100",
            name="ck_purchase_lines_tax_rate_range",
        ),
        CheckConstraint("line_subtotal >= 0", name="ck_purchase_lines_subtotal_non_negative"),
        CheckConstraint("line_tax >= 0", name="ck_purchase_lines_tax_non_negative"),
        CheckConstraint("line_total >= 0", name="ck_purchase_lines_total_non_negative"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    purchase_invoice_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("purchase_invoices.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    item_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("items.id", ondelete="RESTRICT"), index=True
    )
    description: Mapped[str] = mapped_column(Text, nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    unit_cost: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
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

    purchase_invoice: Mapped[PurchaseInvoice] = relationship(back_populates="lines")
    item: Mapped[Item | None] = relationship(back_populates="purchase_lines")
