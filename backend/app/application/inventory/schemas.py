"""Schemas Pydantic del módulo de inventario."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Annotated, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.domain.models.stock import StockMovementType

Quantity = Annotated[Decimal, Field(max_digits=18, decimal_places=4, gt=0)]
UnitCost = Annotated[Decimal, Field(max_digits=18, decimal_places=4, ge=0)]


class WarehouseCreate(BaseModel):
    """Datos para crear una bodega."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    name: str = Field(min_length=1, max_length=200)
    code: str = Field(min_length=1, max_length=50)
    is_active: bool = True


class WarehouseUpdate(BaseModel):
    """Actualización parcial de una bodega."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=200)
    code: str | None = Field(default=None, min_length=1, max_length=50)
    is_active: bool | None = None

    @model_validator(mode="after")
    def validate_update_fields(self) -> Self:
        """Evita updates vacíos y valores nulos en campos obligatorios."""
        if not self.model_fields_set:
            raise ValueError("Debe enviar al menos un campo editable")
        if "name" in self.model_fields_set and self.name is None:
            raise ValueError("name no puede ser null")
        if "code" in self.model_fields_set and self.code is None:
            raise ValueError("code no puede ser null")
        if "is_active" in self.model_fields_set and self.is_active is None:
            raise ValueError("is_active no puede ser null")
        return self


class WarehouseRead(BaseModel):
    """Representación pública de una bodega."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    code: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


class StockMovementCreate(BaseModel):
    """Datos para registrar un movimiento de stock."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    item_id: UUID
    warehouse_id: UUID
    movement_type: StockMovementType
    quantity: Quantity
    unit_cost: UnitCost | None = None
    reference: str | None = Field(default=None, max_length=100)


class StockMovementRead(BaseModel):
    """Representación pública de un movimiento de stock."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    item_id: UUID
    warehouse_id: UUID
    movement_type: StockMovementType
    quantity: Decimal
    unit_cost: Decimal | None
    reference: str | None
    created_at: datetime


class StockBalanceRead(BaseModel):
    """Saldo actual por ítem y bodega."""

    model_config = ConfigDict(from_attributes=True)

    item_id: UUID
    item_name: str
    warehouse_id: UUID
    warehouse_name: str
    quantity: Decimal
    updated_at: datetime
