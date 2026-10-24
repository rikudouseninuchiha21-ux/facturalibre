"""Modelos de identidad: usuarios y sesiones opacas."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    String,
    Uuid,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.database import Base


class UserRole(enum.StrEnum):
    ADMIN = "ADMIN"
    ACCOUNTANT = "ACCOUNTANT"
    CASHIER = "CASHIER"


def _enum_values(enum_cls: type[enum.StrEnum]) -> list[str]:
    """Persiste los valores, no los nombres, de los enums."""
    return [member.value for member in enum_cls]


class User(Base):
    """Usuario de la aplicación.

    El email se normaliza a minúsculas antes de persistirlo para que la
    restricción UNIQUE sea consistente.
    """

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(200), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        Enum(
            UserRole,
            name="user_role",
            native_enum=True,
            values_callable=_enum_values,
        ),
        nullable=False,
        default=UserRole.ADMIN,
        server_default=text("'ADMIN'"),
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("true"),
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    sessions: Mapped[list[AuthSession]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )


class AuthSession(Base):
    """Sesión opaca revocable.

    ``token`` guarda el hash SHA-256 del token entregado en la cookie. El valor
    original nunca se persiste, de modo que una lectura de la base no permite
    reutilizar sesiones.
    """

    __tablename__ = "sessions"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    token: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        unique=True,
        comment="Hash SHA-256 del token de sesión; el token original no se almacena.",
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    user: Mapped[User] = relationship(back_populates="sessions")
