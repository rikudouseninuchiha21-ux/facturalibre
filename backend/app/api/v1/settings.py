"""Rutas de configuración de la empresa."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies.auth import get_current_user, require_role
from app.application.company_settings_schemas import (
    CompanySettingRead,
    CompanySettingUpdate,
)
from app.domain.company_setting_repository import CompanySettingRepository
from app.domain.models.auth import User, UserRole
from app.infrastructure.database import get_db

router = APIRouter(
    prefix="/settings",
    tags=["settings"],
    dependencies=[Depends(get_current_user)],
)

DbSession = Annotated[Session, Depends(get_db)]


def get_company_setting_repository(db: DbSession) -> CompanySettingRepository:
    """Construye el repositorio de configuración de la empresa."""
    return CompanySettingRepository(db)


CompanySettingRepositoryDep = Annotated[
    CompanySettingRepository, Depends(get_company_setting_repository)
]


@router.get("/company", response_model=CompanySettingRead)
def get_company_settings(
    repository: CompanySettingRepositoryDep,
) -> CompanySettingRead:
    """Devuelve la configuración de la empresa."""
    company = repository.get()
    if company is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Configuración de la empresa no encontrada",
        )
    return CompanySettingRead.model_validate(company)


@router.put("/company", response_model=CompanySettingRead)
def update_company_settings(
    payload: CompanySettingUpdate,
    repository: CompanySettingRepositoryDep,
    current_user: User = Depends(require_role([UserRole.ADMIN])),  # noqa: B008
) -> CompanySettingRead:
    """Actualiza la configuración de la empresa (solo ADMIN)."""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tiene permisos para acceder a este recurso",
        )
    company = repository.update(
        name=payload.name,
        tax_id=payload.tax_id,
        address=payload.address,
        phone=payload.phone,
        email=payload.email,
        logo_url=payload.logo_url,
    )
    if company is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Configuración de la empresa no encontrada",
        )
    return CompanySettingRead.model_validate(company)
