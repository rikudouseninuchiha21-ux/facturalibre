"""Schemas Pydantic para activos fijos y su depreciación."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.domain.models.fixed_asset import FixedAssetStatus

PositiveMoney = Annotated[Decimal, Field(max_digits=18, decimal_places=2, gt=0)]
NonNegativeMoney = Annotated[Decimal, Field(max_digits=18, decimal_places=2, ge=0)]


class FixedAssetCreate(BaseModel):
    """Datos para registrar un activo fijo."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    code: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=1, max_length=200)
    purchase_date: date
    initial_cost: PositiveMoney
    salvage_value: NonNegativeMoney = Decimal("0.00")
    useful_life_months: int = Field(ge=1, le=1200)


class DepreciateAssetRequest(BaseModel):
    """Mes y año del periodo que se desea depreciar."""

    model_config = ConfigDict(extra="forbid")

    month: int = Field(ge=1, le=12)
    year: int = Field(ge=2000, le=9999)


class FixedAssetRead(BaseModel):
    """Representación pública de un activo con sus valores calculados."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    code: str
    name: str
    purchase_date: date
    initial_cost: Decimal
    salvage_value: Decimal
    useful_life_months: int
    status: FixedAssetStatus
    monthly_depreciation: Decimal
    accumulated_depreciation: Decimal
    current_value: Decimal
    is_fully_depreciated: bool
    created_at: datetime


__all__ = ["DepreciateAssetRequest", "FixedAssetCreate", "FixedAssetRead"]
