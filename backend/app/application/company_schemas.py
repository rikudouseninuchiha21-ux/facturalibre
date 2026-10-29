"""Schemas para la administración de empresas y membresías."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.domain.models.auth import UserRole


class CompanyCreate(BaseModel):
    """Datos para dar de alta una empresa."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    name: str = Field(min_length=1, max_length=200)
    tax_id: str | None = Field(default=None, max_length=30)
    dv: str | None = Field(default=None, max_length=2)
    address: str | None = Field(default=None, max_length=300)
    phone: str | None = Field(default=None, max_length=30)
    email: EmailStr | None = None
    tax_regime: str | None = Field(default=None, max_length=20)
    person_type: str | None = Field(default=None, max_length=20)
    fiscal_responsibility: str | None = Field(default=None, max_length=50)
    dian_municipality_code: str | None = Field(default=None, max_length=5)
    dian_department_code: str | None = Field(default=None, max_length=2)


class CompanyRead(BaseModel):
    """Representación pública de una empresa."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    tax_id: str | None
    dv: str | None
    address: str | None
    phone: str | None
    email: str | None
    tax_regime: str | None
    person_type: str | None
    fiscal_responsibility: str | None
    dian_municipality_code: str | None
    dian_department_code: str | None
    created_at: datetime
    updated_at: datetime


class CompanyMembershipRead(BaseModel):
    """Empresa y rol del usuario en ella."""

    company: CompanyRead
    role: UserRole


class CompanyUserAssign(BaseModel):
    """Asignación de un usuario existente a una empresa."""

    model_config = ConfigDict(extra="forbid")

    user_id: UUID
    role: UserRole = UserRole.ACCOUNTANT


class CompanyUserRead(BaseModel):
    """Usuario miembro de una empresa."""

    user_id: UUID
    email: EmailStr
    full_name: str
    role: UserRole
    is_active: bool
