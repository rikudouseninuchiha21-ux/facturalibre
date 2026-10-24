"""Schemas Pydantic para configuración de la empresa."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CompanySettingCreate(BaseModel):
    """Datos para crear la configuración de la empresa."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    name: str = Field(min_length=1, max_length=200)
    tax_id: str | None = Field(default=None, max_length=30)
    address: str | None = Field(default=None, max_length=300)
    phone: str | None = Field(default=None, max_length=30)
    email: str | None = Field(default=None, max_length=255)
    logo_url: str | None = Field(default=None, max_length=500)


class CompanySettingUpdate(BaseModel):
    """Datos para actualizar la configuración de la empresa."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=200)
    tax_id: str | None = Field(default=None, max_length=30)
    address: str | None = Field(default=None, max_length=300)
    phone: str | None = Field(default=None, max_length=30)
    email: str | None = Field(default=None, max_length=255)
    logo_url: str | None = Field(default=None, max_length=500)


class CompanySettingRead(BaseModel):
    """Representación pública de la configuración de la empresa."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    tax_id: str | None
    address: str | None
    phone: str | None
    email: str | None
    logo_url: str | None
    created_at: datetime
    updated_at: datetime
