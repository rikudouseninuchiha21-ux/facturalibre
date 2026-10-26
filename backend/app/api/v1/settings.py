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
from app.domain.models.auth import UserRole
from app.infrastructure.database import get_db
from app.infrastructure.transactions import operation_transaction

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


@router.put(
    "/company",
    response_model=CompanySettingRead,
    dependencies=[Depends(require_role([UserRole.ADMIN]))],
)
def update_company_settings(
    payload: CompanySettingUpdate,
    db: DbSession,
    repository: CompanySettingRepositoryDep,
) -> CompanySettingRead:
    """Actualiza la configuración de la empresa (solo ADMIN).

    La escritura vive dentro de ``operation_transaction``: ``get_db`` no
    commitea al cerrar la sesión, así que sin este bloque el PUT flush-eaba
    pero el cambio se perdía con el ``close()`` (regla de oro de
    transacciones del proyecto).
    """
    with operation_transaction(db):
        company = repository.update(values=payload.model_dump(exclude_unset=True))
    return CompanySettingRead.model_validate(company)
