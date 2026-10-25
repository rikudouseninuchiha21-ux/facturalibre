"""Modelos de activos fijos y su depreciación mensual.

La depreciación se calcula por línea recta sobre la base depreciable
``initial_cost - salvage_value``. Cada registro mensual genera un asiento
contable independiente y queda vinculado a él mediante
``accounting_entry_id``.
"""

from __future__ import annotations

import enum
import uuid
from datetime import date, datetime
from decimal import ROUND_HALF_UP, Decimal

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

from app.infrastructure.database import Base

TWOPLACES = Decimal("0.01")


class FixedAssetStatus(enum.StrEnum):
    """Estado operativo de un activo fijo."""

    ACTIVE = "ACTIVE"
    DISPOSED = "DISPOSED"


def _enum_values(enum_cls: type[enum.StrEnum]) -> list[str]:
    """Persiste los valores, no los nombres, de los enums."""
    return [member.value for member in enum_cls]


class FixedAsset(Base):
    """Activo fijo sujeto a depreciación por línea recta."""

    __tablename__ = "fixed_assets"

    __table_args__ = (
        UniqueConstraint("code", name="uq_fixed_assets_code"),
        CheckConstraint("initial_cost > 0", name="ck_fixed_assets_initial_cost_positive"),
        CheckConstraint("salvage_value >= 0", name="ck_fixed_assets_salvage_value_non_negative"),
        CheckConstraint(
            "salvage_value < initial_cost",
            name="ck_fixed_assets_salvage_value_less_than_cost",
        ),
        CheckConstraint(
            "useful_life_months > 0",
            name="ck_fixed_assets_useful_life_positive",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    code: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    purchase_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    initial_cost: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    salvage_value: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        nullable=False,
        default=Decimal("0.00"),
        server_default=text("0"),
    )
    useful_life_months: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[FixedAssetStatus] = mapped_column(
        Enum(
            FixedAssetStatus,
            name="fixed_asset_status",
            native_enum=True,
            values_callable=_enum_values,
        ),
        nullable=False,
        default=FixedAssetStatus.ACTIVE,
        server_default=text("'ACTIVE'"),
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    depreciation_entries: Mapped[list[DepreciationEntry]] = relationship(
        back_populates="asset",
        cascade="all, delete-orphan",
        order_by="DepreciationEntry.date",
    )

    @property
    def accumulated_depreciation(self) -> Decimal:
        """Suma de las depreciaciones registradas, redondeada a dos decimales."""
        total = sum(
            (entry.amount for entry in self.depreciation_entries),
            Decimal("0.00"),
        )
        return total.quantize(TWOPLACES)

    @property
    def current_value(self) -> Decimal:
        """Valor neto del activo: costo inicial menos depreciación acumulada."""
        return (self.initial_cost - self.accumulated_depreciation).quantize(TWOPLACES)

    @property
    def monthly_depreciation(self) -> Decimal:
        """Cuota mensual teórica por línea recta."""
        base = self.initial_cost - self.salvage_value
        return (base / Decimal(self.useful_life_months)).quantize(
            TWOPLACES,
            rounding=ROUND_HALF_UP,
        )

    @property
    def is_fully_depreciated(self) -> bool:
        """Indica si ya se consumió toda la base depreciable."""
        base = (self.initial_cost - self.salvage_value).quantize(TWOPLACES)
        return self.accumulated_depreciation >= base


class DepreciationEntry(Base):
    """Cuota mensual de depreciación de un activo fijo.

    La fecha se guarda como el último día del mes depreciado. La restricción
    única ``(asset_id, date)`` impide registrar dos cuotas para el mismo mes,
    incluso ante peticiones concurrentes.
    """

    __tablename__ = "depreciation_entries"

    __table_args__ = (
        UniqueConstraint(
            "asset_id",
            "date",
            name="uq_depreciation_entries_asset_id_date",
        ),
        CheckConstraint("amount > 0", name="ck_depreciation_entries_amount_positive"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    asset_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("fixed_assets.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    accounting_entry_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("accounting_entries.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    asset: Mapped[FixedAsset] = relationship(back_populates="depreciation_entries")


__all__ = ["DepreciationEntry", "FixedAsset", "FixedAssetStatus"]
