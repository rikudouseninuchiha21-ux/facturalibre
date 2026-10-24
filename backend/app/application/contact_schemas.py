"""Schemas Pydantic para el recurso Contact."""

from datetime import datetime
from typing import Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator

from app.domain.models.contact import ContactStatus, ContactType


class ContactCreate(BaseModel):
    """Datos para crear un contacto."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    name: str = Field(min_length=1, max_length=200)
    email: EmailStr | None = None
    tax_id: str | None = Field(default=None, max_length=30)
    type: ContactType = ContactType.CUSTOMER
    status: ContactStatus = ContactStatus.CUSTOMER


class ContactUpdate(BaseModel):
    """Actualización parcial; version es obligatoria para el bloqueo optimista."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=200)
    email: EmailStr | None = None
    tax_id: str | None = Field(default=None, max_length=30)
    type: ContactType | None = None
    status: ContactStatus | None = None
    version: int = Field(ge=1)

    @model_validator(mode="after")
    def validate_update_fields(self) -> Self:
        """Evita updates vacíos y permite limpiar email/tax_id, pero no name."""
        if "name" in self.model_fields_set and self.name is None:
            raise ValueError("name no puede ser null")
        if not (self.model_fields_set - {"version"}):
            raise ValueError("Debe enviar al menos un campo editable además de version")
        return self


class ContactRead(BaseModel):
    """Representación pública de un contacto activo."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    email: EmailStr | None
    tax_id: str | None
    type: ContactType
    status: ContactStatus
    version: int
    created_at: datetime
    updated_at: datetime
