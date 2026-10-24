"""Repositorio de configuración de la empresa."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.exceptions import ResourceNotFoundError
from app.domain.models.company_setting import CompanySetting


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

    def update(
        self,
        *,
        name: str | None = None,
        tax_id: str | None = None,
        address: str | None = None,
        phone: str | None = None,
        email: str | None = None,
        logo_url: str | None = None,
    ) -> CompanySetting:
        """Actualiza la configuración de la empresa."""
        company = self.get()
        if company is None:
            raise ResourceNotFoundError("Configuración de empresa no encontrada")

        if name is not None:
            company.name = name
        if tax_id is not None:
            company.tax_id = tax_id
        if address is not None:
            company.address = address
        if phone is not None:
            company.phone = phone
        if email is not None:
            company.email = email
        if logo_url is not None:
            company.logo_url = logo_url

        self.db.flush()
        self.db.refresh(company)
        return company
