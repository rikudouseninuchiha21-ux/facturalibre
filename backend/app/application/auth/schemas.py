"""Schemas Pydantic del módulo de autenticación."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.domain.models.auth import UserRole

MAX_PASSWORD_BYTES = 72


class RegisterRequest(BaseModel):
    """Datos para dar de alta al usuario inicial."""

    model_config = ConfigDict(extra="forbid")

    email: EmailStr
    password: str = Field(min_length=8, max_length=MAX_PASSWORD_BYTES)
    full_name: str = Field(min_length=1, max_length=200)
    role: UserRole = UserRole.ADMIN

    @field_validator("full_name")
    @classmethod
    def normalize_full_name(cls, value: str) -> str:
        """Evita nombres compuestos solo por espacios."""
        normalized = value.strip()
        if not normalized:
            raise ValueError("El nombre completo es obligatorio")
        return normalized

    @field_validator("password")
    @classmethod
    def validate_password_bytes(cls, value: str) -> str:
        """bcrypt solo procesa 72 bytes; se rechaza el exceso de forma explícita."""
        if len(value.encode("utf-8")) > MAX_PASSWORD_BYTES:
            raise ValueError("La contraseña no puede superar 72 bytes")
        return value


class LoginRequest(BaseModel):
    """Credenciales para iniciar sesión."""

    model_config = ConfigDict(extra="forbid")

    email: EmailStr
    password: str = Field(min_length=1, max_length=MAX_PASSWORD_BYTES)

    @field_validator("password")
    @classmethod
    def validate_password_bytes(cls, value: str) -> str:
        """Mantiene el mismo límite que bcrypt en el login."""
        if len(value.encode("utf-8")) > MAX_PASSWORD_BYTES:
            raise ValueError("La contraseña no puede superar 72 bytes")
        return value


class UserRead(BaseModel):
    """Representación pública de un usuario; nunca incluye el hash."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: EmailStr
    full_name: str
    role: UserRole
    is_active: bool
    created_at: datetime
