"""Modelo de pagos recibidos."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    Uuid,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.database import Base

if TYPE_CHECKING:
    from app.domain.models.invoice import Invoice


class Payment(Base):
    __tablename__ = "payments"

    __table_args__ = (CheckConstraint("amount > 0", name="ck_payments_amount_positive"),)

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    invoice_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("invoices.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    payment_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    # -- REQUIERE VALIDACIÓN: contador/experto DIAN (catálogo de medios de pago).
    method: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment=("REQUIERE VALIDACIÓN: contador/experto DIAN. Catálogo de medios de pago."),
    )
    reference: Mapped[str | None] = mapped_column(String(100))
    bank_movement_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("bank_transactions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Movimiento bancario conciliado con este pago.",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    invoice: Mapped[Invoice] = relationship(back_populates="payments")
