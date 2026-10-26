"""Schemas Pydantic para configuración de la empresa."""

from __future__ import annotations

import enum
from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class DianEnvironment(enum.StrEnum):
    """Ambiente de facturación electrónica DIAN."""

    HABILITACION = "HABILITACION"
    PRODUCCION = "PRODUCCION"


class CompanySettingCreate(BaseModel):
    """Datos para crear la configuración de la empresa."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    name: str = Field(min_length=1, max_length=200)
    tax_id: str | None = Field(default=None, max_length=30)
    address: str | None = Field(default=None, max_length=300)
    phone: str | None = Field(default=None, max_length=30)
    email: str | None = Field(default=None, max_length=255)
    logo_url: str | None = Field(default=None, max_length=500)

    # -- Fase 38A: datos DIAN de la empresa (NIT = tax_id).
    dv: str | None = Field(default=None, max_length=2)
    tax_regime: str | None = Field(default=None, max_length=20)
    person_type: str | None = Field(default=None, max_length=20)
    fiscal_responsibility: str | None = Field(default=None, max_length=50)
    dian_municipality_code: str | None = Field(default=None, max_length=5)
    dian_department_code: str | None = Field(default=None, max_length=2)
    country_code: str | None = Field(default=None, max_length=3)
    dian_resolution_number: str | None = Field(default=None, max_length=20)
    dian_resolution_prefix: str | None = Field(default=None, max_length=4)
    dian_resolution_range_from: int | None = Field(default=None)
    dian_resolution_range_to: int | None = Field(default=None)
    dian_resolution_valid_from: date | None = Field(default=None)
    dian_resolution_valid_to: date | None = Field(default=None)
    dian_software_id: str | None = Field(default=None, max_length=100)
    dian_software_pin: str | None = Field(default=None, max_length=100)
    dian_environment: DianEnvironment = DianEnvironment.HABILITACION


class CompanySettingUpdate(CompanySettingCreate):
    """Datos para actualizar la configuración de la empresa."""

    name: str | None = Field(default=None, min_length=1, max_length=200)  # type: ignore[assignment]


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
    dv: str | None
    tax_regime: str | None
    person_type: str | None
    fiscal_responsibility: str | None
    dian_municipality_code: str | None
    dian_department_code: str | None
    country_code: str
    dian_resolution_number: str | None
    dian_resolution_prefix: str | None
    dian_resolution_range_from: int | None
    dian_resolution_range_to: int | None
    dian_resolution_valid_from: date | None
    dian_resolution_valid_to: date | None
    dian_software_id: str | None
    dian_software_pin: str | None
    dian_environment: DianEnvironment
    created_at: datetime
    updated_at: datetime
