"""Rutas de activos fijos y depreciación mensual."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies.auth import get_current_user, require_role
from app.application.fixed_asset_schemas import (
    DepreciateAssetRequest,
    FixedAssetCreate,
    FixedAssetRead,
)
from app.application.fixed_asset_service import FixedAssetService
from app.domain.fixed_asset_repository import FixedAssetRepository
from app.domain.models.auth import UserRole
from app.infrastructure.database import get_db
from app.infrastructure.transactions import operation_transaction

router = APIRouter(
    prefix="/assets",
    tags=["assets"],
    dependencies=[
        Depends(get_current_user),
        Depends(require_role([UserRole.ADMIN, UserRole.ACCOUNTANT])),
    ],
)

DbSession = Annotated[Session, Depends(get_db)]


def get_fixed_asset_repository(db: DbSession) -> FixedAssetRepository:
    """Construye el repositorio de activos con la sesión de la petición."""
    return FixedAssetRepository(db)


FixedAssetRepositoryDep = Annotated[
    FixedAssetRepository,
    Depends(get_fixed_asset_repository),
]


def get_fixed_asset_service(db: DbSession) -> FixedAssetService:
    """Construye el servicio de activos fijos con la sesión de la petición."""
    return FixedAssetService(db)


FixedAssetServiceDep = Annotated[FixedAssetService, Depends(get_fixed_asset_service)]


@router.post("", response_model=FixedAssetRead, status_code=status.HTTP_201_CREATED)
def create_asset(
    payload: FixedAssetCreate,
    db: DbSession,
    service: FixedAssetServiceDep,
) -> FixedAssetRead:
    """Registra un activo fijo. No genera asiento hasta que se deprecie."""
    with operation_transaction(db):
        asset = service.create_asset(
            code=payload.code,
            name=payload.name,
            purchase_date=payload.purchase_date,
            initial_cost=payload.initial_cost,
            salvage_value=payload.salvage_value,
            useful_life_months=payload.useful_life_months,
        )
    return FixedAssetRead.model_validate(asset)


@router.post("/{asset_id}/depreciate", response_model=FixedAssetRead)
def depreciate_asset(
    asset_id: UUID,
    payload: DepreciateAssetRequest,
    db: DbSession,
    service: FixedAssetServiceDep,
) -> FixedAssetRead:
    """Registra la depreciación del mes y genera su asiento contable.

    La cuota y el asiento se ejecutan en una sola transacción: si falla la
    contabilidad, la cuota no queda persistida.
    """
    with operation_transaction(db):
        asset = service.depreciate_asset(
            asset_id=asset_id,
            year=payload.year,
            month=payload.month,
        )
    return FixedAssetRead.model_validate(asset)


@router.get("", response_model=list[FixedAssetRead])
def list_assets(
    repository: FixedAssetRepositoryDep,
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[FixedAssetRead]:
    """Lista activos con su depreciación acumulada y valor actual."""
    assets = repository.list(limit=limit, offset=offset)
    return [FixedAssetRead.model_validate(asset) for asset in assets]


__all__ = ["router"]
