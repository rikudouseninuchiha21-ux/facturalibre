"""Modelo del catálogo de impuestos."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, Integer, Numeric, String, Uuid, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.domain.models.tenancy import CompanyScopedMixin
from app.infrastructure.database import Base

if TYPE_CHECKING:
    from app.domain.models.item import Item


class Tax(CompanyScopedMixin, Base):
    __tablename__ = "taxes"

    __table_args__ = (CheckConstraint("rate >= 0 AND rate <= 100", name="ck_taxes_rate_range"),)

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    # -- REQUIERE VALIDACIÓN: contador/experto DIAN (tarifa y catálogo de impuestos).
    # Se usa NUMERIC(7,4) para admitir 19.0000 %; NUMERIC(5,4) solo llega a 9.9999 %.
    rate: Mapped[Decimal] = mapped_column(
        Numeric(7, 4),
        nullable=False,
        comment=(
            "REQUIERE VALIDACIÓN: contador/experto DIAN. "
            "Tarifa 0-100 con 4 decimales y catálogo de impuestos."
        ),
    )
    # -- Fase 38A: código y nombre del impuesto según el catálogo DIAN.
    # 01=IVA, 03=ICA, 04=INC, 05=ReteFuente, 06=ReteIVA, 07=ReteICA, 22=bolsas.
    dian_tax_code: Mapped[str | None] = mapped_column(String(2))
    dian_tax_name: Mapped[str | None] = mapped_column(String(50))

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

    items: Mapped[list[Item]] = relationship(back_populates="tax")
