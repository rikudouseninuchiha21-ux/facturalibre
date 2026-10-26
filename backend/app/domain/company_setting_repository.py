"""Repositorio de configuración de la empresa."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.exceptions import ResourceNotFoundError
from app.domain.models.company_setting import CompanySetting

EDITABLE_FIELDS: frozenset[str] = frozenset(
    {
        "name",
        "tax_id",
        "address",
        "phone",
        "email",
        "logo_url",
        "dv",
        "tax_regime",
        "person_type",
        "fiscal_responsibility",
        "dian_municipality_code",
        "dian_department_code",
        "country_code",
        "dian_resolution_number",
        "dian_resolution_prefix",
        "dian_resolution_range_from",
        "dian_resolution_range_to",
        "dian_resolution_valid_from",
        "dian_resolution_valid_to",
        "dian_software_id",
        "dian_software_pin",
        "dian_environment",
    }
)


class CompanySettingRepository:
    """Acceso a datos de configuración de la empresa."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def get(self) -> CompanySetting | None:
        """Devuelve la configuración de la empresa (solo una fila)."""
        return self.db.scalar(select(CompanySetting))

    def create(
        self,
        *,
        name: str,
        tax_id: str | None,
        address: str | None,
        phone: str | None,
        email: str | None,
        logo_url: str | None,
    ) -> CompanySetting:
        """Crea la configuración de la empresa."""
        company = CompanySetting(
            name=name,
            tax_id=tax_id,
            address=address,
            phone=phone,
            email=email,
            logo_url=logo_url,
        )
        self.db.add(company)
        self.db.flush()
        self.db.refresh(company)
        return company

    def update(self, *, values: dict[str, Any]) -> CompanySetting:
        """Aplica solo los campos presentes y no nulos.

        Semántica histórica conservada: un campo omitido o ``None`` no se
        limpia (los PUT del frontend envían el formulario completo).
        """
        company = self.get()
        if company is None:
            raise ResourceNotFoundError("Configuración de empresa no encontrada")

        for key, value in values.items():
            if key in EDITABLE_FIELDS and value is not None:
                setattr(company, key, value)
        self.db.flush()
        self.db.refresh(company)
        return company


__all__ = ["CompanySettingRepository"]
