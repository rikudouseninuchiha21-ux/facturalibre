"""Modelos del libro de movimientos y de saldos de inventario."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Numeric,
    String,
    Uuid,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.domain.models.tenancy import CompanyScopedMixin
from app.infrastructure.database import Base

if TYPE_CHECKING:
    from app.domain.models.item import Item
    from app.domain.models.warehouse import Warehouse


class StockMovementType(enum.StrEnum):
    """Efecto de un movimiento sobre el saldo de la bodega."""

    IN = "IN"
    OUT = "OUT"
    TRANSFER_IN = "TRANSFER_IN"
    TRANSFER_OUT = "TRANSFER_OUT"
    ADJUSTMENT = "ADJUSTMENT"


def _enum_values(enum_cls: type[enum.StrEnum]) -> list[str]:
    """Persiste los valores, no los nombres, de los enums."""
    return [member.value for member in enum_cls]


class StockMovement(CompanyScopedMixin, Base):
    """Movimiento inmutable que explica una variación de stock."""

    __tablename__ = "stock_movements"

    __table_args__ = (
        CheckConstraint("quantity > 0", name="ck_stock_movements_quantity_positive"),
        CheckConstraint(
            "unit_cost IS NULL OR unit_cost >= 0",
            name="ck_stock_movements_unit_cost_non_negative",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    item_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("items.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    warehouse_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("warehouses.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    movement_type: Mapped[StockMovementType] = mapped_column(
        Enum(
            StockMovementType,
            name="stock_movement_type",
            native_enum=True,
            values_callable=_enum_values,
        ),
        nullable=False,
        index=True,
    )
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    # REQUIERE VALIDACIÓN: método de costeo. El MVP solo registra el dato.
    unit_cost: Mapped[Decimal | None] = mapped_column(Numeric(18, 4))
    reference: Mapped[str | None] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), index=True
    )

    item: Mapped[Item] = relationship()
    warehouse: Mapped[Warehouse] = relationship()


class StockBalance(CompanyScopedMixin, Base):
    """Saldo actual por ítem y bodega, derivado del libro de movimientos."""

    __tablename__ = "stock_balances"

    __table_args__ = (
        CheckConstraint(
            "quantity >= 0",
            name="ck_stock_balances_quantity_non_negative",
        ),
    )

    item_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("items.id", ondelete="RESTRICT"),
        primary_key=True,
    )
    warehouse_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("warehouses.id", ondelete="RESTRICT"),
        primary_key=True,
        index=True,
    )
    quantity: Mapped[Decimal] = mapped_column(
        Numeric(18, 4), nullable=False, server_default=text("0")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    item: Mapped[Item] = relationship()
    warehouse: Mapped[Warehouse] = relationship()

    @property
    def item_name(self) -> str:
        """Nombre del ítem para la representación pública del saldo."""
        return self.item.name

    @property
    def warehouse_name(self) -> str:
        """Nombre de la bodega para la representación pública del saldo."""
        return self.warehouse.name
