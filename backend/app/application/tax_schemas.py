"""Schemas Pydantic para el recurso Tax."""

from datetime import datetime
from decimal import Decimal
from typing import Annotated, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

Rate = Annotated[Decimal, Field(max_digits=7, decimal_places=4, ge=0, le=100)]


class TaxCreate(BaseModel):
    """Datos para crear un impuesto."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    name: str = Field(min_length=1, max_length=100)
    rate: Rate


class TaxUpdate(BaseModel):
    """Actualización parcial; version es obligatoria para el bloqueo optimista."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=100)
    rate: Rate | None = None
    version: int = Field(ge=1)

    @model_validator(mode="after")
    def validate_update_fields(self) -> Self:
        """Evita updates vacíos y rechaza null en campos obligatorios."""
        if "name" in self.model_fields_set and self.name is None:
            raise ValueError("name no puede ser null")
        if "rate" in self.model_fields_set and self.rate is None:
            raise ValueError("rate no puede ser null")
        if not (self.model_fields_set - {"version"}):
            raise ValueError("Debe enviar al menos un campo editable además de version")
        return self


class TaxRead(BaseModel):
    """Representación pública de un impuesto activo."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    rate: Decimal
    version: int
    created_at: datetime
    updated_at: datetime
