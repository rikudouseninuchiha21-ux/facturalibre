"""Schemas Pydantic para el recurso Item."""

from datetime import datetime
from decimal import Decimal
from typing import Annotated, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

Money = Annotated[Decimal, Field(max_digits=18, decimal_places=2, ge=0)]


class ItemCreate(BaseModel):
    """Datos para crear un ítem."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    name: str = Field(min_length=1, max_length=200)
    description: str | None = None
    unit_price: Money
    tax_id: UUID | None = None
    price_includes_tax: bool = False


class ItemUpdate(BaseModel):
    """Actualización parcial; version es obligatoria para el bloqueo optimista."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    unit_price: Money | None = None
    tax_id: UUID | None = None
    price_includes_tax: bool | None = None
    version: int = Field(ge=1)

    @model_validator(mode="after")
    def validate_update_fields(self) -> Self:
        """Evita updates vacíos; description/tax_id sí pueden quedar en null."""
        if "name" in self.model_fields_set and self.name is None:
            raise ValueError("name no puede ser null")
        if "unit_price" in self.model_fields_set and self.unit_price is None:
            raise ValueError("unit_price no puede ser null")
        if not (self.model_fields_set - {"version"}):
            raise ValueError("Debe enviar al menos un campo editable además de version")
        return self


class ItemRead(BaseModel):
    """Representación pública de un ítem activo."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    description: str | None
    unit_price: Decimal
    tax_id: UUID | None
    price_includes_tax: bool
    version: int
    created_at: datetime
    updated_at: datetime
