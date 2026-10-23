"""Rutas CRUD para bodegas."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.dependencies.auth import get_current_user
from app.application.inventory.schemas import (
    WarehouseCreate,
    WarehouseRead,
    WarehouseUpdate,
)
from app.domain.exceptions import ResourceNotFoundError
from app.domain.warehouse_repository import WarehouseRepository
from app.infrastructure.database import get_db

router = APIRouter(
    prefix="/warehouses",
    tags=["warehouses"],
    dependencies=[Depends(get_current_user)],
)

DbSession = Annotated[Session, Depends(get_db)]
WAREHOUSE_CODE_CONFLICT = "El código de bodega ya existe"


def get_warehouse_repository(db: DbSession) -> WarehouseRepository:
    """Construye el repositorio con la sesión de la petición."""
    return WarehouseRepository(db)


WarehouseRepositoryDep = Annotated[WarehouseRepository, Depends(get_warehouse_repository)]


@router.post("", response_model=WarehouseRead, status_code=status.HTTP_201_CREATED)
def create_warehouse(
    payload: WarehouseCreate,
    repository: WarehouseRepositoryDep,
) -> WarehouseRead:
    """Crea una bodega."""
    try:
        warehouse = repository.create(payload.model_dump())
    except IntegrityError:
        repository.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=WAREHOUSE_CODE_CONFLICT,
        ) from None
    return WarehouseRead.model_validate(warehouse)


@router.get("", response_model=list[WarehouseRead])
def list_warehouses(
    repository: WarehouseRepositoryDep,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
    is_active: bool | None = None,
) -> list[WarehouseRead]:
    """Lista bodegas, opcionalmente filtradas por estado."""
    warehouses = repository.list(
        limit=limit,
        offset=offset,
        is_active=is_active,
    )
    return [WarehouseRead.model_validate(warehouse) for warehouse in warehouses]


@router.get("/{warehouse_id}", response_model=WarehouseRead)
def get_warehouse(
    warehouse_id: UUID,
    repository: WarehouseRepositoryDep,
) -> WarehouseRead:
    """Obtiene una bodega por id."""
    warehouse = repository.get_by_id(warehouse_id)
    if warehouse is None:
        raise ResourceNotFoundError("Bodega no encontrada")
    return WarehouseRead.model_validate(warehouse)


@router.patch("/{warehouse_id}", response_model=WarehouseRead)
def update_warehouse(
    warehouse_id: UUID,
    payload: WarehouseUpdate,
    repository: WarehouseRepositoryDep,
) -> WarehouseRead:
    """Actualiza nombre, código o estado de una bodega."""
    values = payload.model_dump(exclude_unset=True)
    try:
        warehouse = repository.update(warehouse_id, values)
    except IntegrityError:
        repository.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=WAREHOUSE_CODE_CONFLICT,
        ) from None
    return WarehouseRead.model_validate(warehouse)


@router.delete("/{warehouse_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_warehouse(
    warehouse_id: UUID,
    repository: WarehouseRepositoryDep,
) -> Response:
    """Desactiva una bodega sin borrar su historial de movimientos."""
    repository.deactivate(warehouse_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
