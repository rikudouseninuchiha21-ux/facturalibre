"""Schemas Pydantic para centros de costo."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CostCenterCreate(BaseModel):
    """Datos para crear un centro de costo."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    code: str = Field(min_length=1, max_length=20)
    name: str = Field(min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=2000)


class CostCenterUpdate(BaseModel):
    """Datos parciales para actualizar un centro de costo."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    code: str | None = Field(default=None, min_length=1, max_length=20)
    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=2000)
    is_active: bool | None = None


class CostCenterRead(BaseModel):
    """Representación pública de un centro de costo."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    code: str
    name: str
    description: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime


__all__ = [
    "CostCenterCreate",
    "CostCenterRead",
    "CostCenterUpdate",
]
