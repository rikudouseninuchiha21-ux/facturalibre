"""Modelo de líneas de cotización."""

from __future__ import annotations

import uuid
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Numeric,
    Text,
    Uuid,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.database import Base

if TYPE_CHECKING:
    from app.domain.models.item import Item
    from app.domain.models.quote import Quote


class QuoteLine(Base):
    __tablename__ = "quote_lines"

    __table_args__ = (
        CheckConstraint("quantity > 0", name="ck_quote_lines_quantity_positive"),
        CheckConstraint("unit_price >= 0", name="ck_quote_lines_unit_price_non_negative"),
        CheckConstraint(
            "tax_rate >= 0 AND tax_rate <= 100",
            name="ck_quote_lines_tax_rate_range",
        ),
        CheckConstraint("line_subtotal >= 0", name="ck_quote_lines_subtotal_non_negative"),
        CheckConstraint("line_tax >= 0", name="ck_quote_lines_tax_non_negative"),
        CheckConstraint("line_total >= 0", name="ck_quote_lines_total_non_negative"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    quote_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("quotes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    item_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("items.id", ondelete="RESTRICT"), index=True
    )
    description: Mapped[str] = mapped_column(Text, nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    tax_rate: Mapped[Decimal] = mapped_column(
        Numeric(7, 4),
        nullable=False,
        server_default=text("0"),
        comment=("REQUIERE VALIDACIÓN: contador/experto DIAN. Tarifa y código de impuesto."),
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

    quote: Mapped[Quote] = relationship(back_populates="lines")
    item: Mapped[Item | None] = relationship(back_populates="quote_lines")


__all__ = ["QuoteLine"]
