"""Schemas Pydantic para la gestión de usuarios."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.domain.models.auth import UserRole

MAX_PASSWORD_BYTES = 72


class UserCreate(BaseModel):
    """Datos para crear un usuario (solo ADMIN)."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    email: EmailStr
    password: str = Field(min_length=8, max_length=MAX_PASSWORD_BYTES)
    full_name: str = Field(min_length=1, max_length=200)
    role: UserRole = UserRole.ADMIN


class UserUpdate(BaseModel):
    """Datos para actualizar un usuario (solo ADMIN)."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    email: str | None = Field(default=None, max_length=255)
    full_name: str | None = Field(default=None, min_length=1, max_length=200)
    role: UserRole | None = None
    is_active: bool | None = None


class UserRead(BaseModel):
    """Representación pública de un usuario."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: EmailStr
    full_name: str
    role: UserRole
    is_active: bool
    created_at: datetime
