"""Modelo de configuración de la empresa."""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import (
    BigInteger,
    Date,
    DateTime,
    String,
    UniqueConstraint,
    Uuid,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.domain.models.tenancy import CompanyScopedMixin
from app.infrastructure.database import Base


class CompanySetting(CompanyScopedMixin, Base):
    """Configuración de la empresa para facturación y reportes."""

    __tablename__ = "company_settings"
    __table_args__ = (UniqueConstraint("company_id", name="uq_company_settings_company_id"),)

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    tax_id: Mapped[str | None] = mapped_column(String(30), nullable=True)
    address: Mapped[str | None] = mapped_column(String(300), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    logo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    # -- Fase 38A: datos de facturación electrónica DIAN.
    # El NIT vive en ``tax_id`` (columna preexistente).
    dv: Mapped[str | None] = mapped_column(String(2), nullable=True)
    tax_regime: Mapped[str | None] = mapped_column(String(20), nullable=True)
    person_type: Mapped[str | None] = mapped_column(String(20), nullable=True)
    fiscal_responsibility: Mapped[str | None] = mapped_column(String(50), nullable=True)
    dian_municipality_code: Mapped[str | None] = mapped_column(String(5), nullable=True)
    dian_department_code: Mapped[str | None] = mapped_column(String(2), nullable=True)
    country_code: Mapped[str] = mapped_column(
        String(3), nullable=False, server_default=text("'CO'")
    )
    dian_resolution_number: Mapped[str | None] = mapped_column(String(20), nullable=True)
    dian_resolution_prefix: Mapped[str | None] = mapped_column(String(4), nullable=True)
    dian_resolution_range_from: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    dian_resolution_range_to: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    dian_resolution_valid_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    dian_resolution_valid_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    dian_software_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    # PIN del software proveedor. En reposo debería cifrarse (Fase 38B);
    # hoy solo se usa para el CUFE local.
    dian_software_pin: Mapped[str | None] = mapped_column(String(100), nullable=True)
    dian_environment: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default=text("'HABILITACION'")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
