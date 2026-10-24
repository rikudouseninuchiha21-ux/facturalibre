"""Modelo de ítems (productos y servicios)."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, Text, Uuid, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.database import Base

if TYPE_CHECKING:
    from app.domain.models.invoice_line import InvoiceLine
    from app.domain.models.purchase import PurchaseLine
    from app.domain.models.quote_line import QuoteLine
    from app.domain.models.tax import Tax


class Item(Base):
    __tablename__ = "items"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    unit_price: Mapped[Decimal] = mapped_column(
        Numeric(18, 2), nullable=False, server_default=text("0")
    )
    tax_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("taxes.id", ondelete="RESTRICT"), index=True
    )

    # DECISIONES.md: bloqueo optimista y soft delete en datos maestros.
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
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    tax: Mapped[Tax | None] = relationship(back_populates="items")
    invoice_lines: Mapped[list[InvoiceLine]] = relationship(back_populates="item")
    purchase_lines: Mapped[list[PurchaseLine]] = relationship(back_populates="item")
    quote_lines: Mapped[list[QuoteLine]] = relationship(back_populates="item")
