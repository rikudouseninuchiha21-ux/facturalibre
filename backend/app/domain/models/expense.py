"""Modelo de gastos operativos."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Uuid,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.domain.models.tenancy import CompanyScopedMixin
from app.infrastructure.database import Base


class Expense(CompanyScopedMixin, Base):
    """Gasto operativo (arriendo, servicios, papelería, etc.).

    Cada gasto genera automáticamente un asiento contable:
    débito a Gastos diversos (5199) y crédito a Caja o Bancos
    según el método de pago.
    """

    __tablename__ = "expenses"

    __table_args__ = (CheckConstraint("amount > 0", name="ck_expenses_amount_positive"),)

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    concept: Mapped[str] = mapped_column(String(200), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    payment_method: Mapped[str] = mapped_column(String(50), nullable=False)
    reference: Mapped[str | None] = mapped_column(String(200), nullable=True)
    bank_movement_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("bank_transactions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Movimiento bancario conciliado con este gasto.",
    )
    # Dimensión opcional de centro de costo; se propaga al asiento del gasto.
    cost_center_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("cost_centers.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
        comment="Centro de costo al que se atribuye el gasto.",
    )

    # DECISIONES.md: bloqueo optimista y soft delete en datos transaccionales.
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


__all__ = ["Expense"]
