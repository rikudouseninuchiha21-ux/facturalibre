"""Modelos de empresas y de acceso multiusuario por empresa."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    String,
    UniqueConstraint,
    Uuid,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.domain.models.auth import UserRole
from app.infrastructure.database import Base


def _enum_values(enum_cls: type[UserRole]) -> list[str]:
    """Persiste los valores, no los nombres, del enum de roles."""
    return [member.value for member in enum_cls]


class Company(Base):
    """Empresa (tenant) con su identificación fiscal."""

    __tablename__ = "companies"

    __table_args__ = (UniqueConstraint("tax_id", name="uq_companies_tax_id"),)

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    tax_id: Mapped[str | None] = mapped_column(String(30))
    dv: Mapped[str | None] = mapped_column(String(2))
    address: Mapped[str | None] = mapped_column(String(300))
    phone: Mapped[str | None] = mapped_column(String(30))
    email: Mapped[str | None] = mapped_column(String(255))
    tax_regime: Mapped[str | None] = mapped_column(String(20))
    person_type: Mapped[str | None] = mapped_column(String(20))
    fiscal_responsibility: Mapped[str | None] = mapped_column(String(50))
    dian_municipality_code: Mapped[str | None] = mapped_column(String(5))
    dian_department_code: Mapped[str | None] = mapped_column(String(2))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class UserCompany(Base):
    """Acceso de un usuario a una empresa, con su rol en ese tenant."""

    __tablename__ = "user_companies"

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    company_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("companies.id", ondelete="CASCADE"),
        primary_key=True,
    )
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
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


__all__ = ["Company", "UserCompany"]
