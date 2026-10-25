"""Rutas de centros de costo."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.api.dependencies.auth import get_current_user, require_role
from app.application.cost_center_schemas import (
    CostCenterCreate,
    CostCenterRead,
    CostCenterUpdate,
)
from app.application.cost_center_service import CostCenterService
from app.domain.models.auth import UserRole
from app.infrastructure.database import get_db
from app.infrastructure.transactions import operation_transaction

router = APIRouter(
    prefix="/cost-centers",
    tags=["cost-centers"],
    dependencies=[Depends(get_current_user)],
)

DbSession = Annotated[Session, Depends(get_db)]


def get_cost_center_service(db: DbSession) -> CostCenterService:
    """Construye el servicio de centros de costo con la sesión de la petición."""
    return CostCenterService(db)


CostCenterServiceDep = Annotated[CostCenterService, Depends(get_cost_center_service)]


@router.get(
    "",
    response_model=list[CostCenterRead],
    dependencies=[Depends(require_role([UserRole.ADMIN, UserRole.ACCOUNTANT, UserRole.CASHIER]))],
)
def list_cost_centers(
    service: CostCenterServiceDep,
    include_inactive: Annotated[bool, Query()] = False,
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[CostCenterRead]:
    """Lista centros de costo; por defecto solo los activos."""
    centers = service.list(
        include_inactive=include_inactive,
        limit=limit,
        offset=offset,
    )
    return [CostCenterRead.model_validate(center) for center in centers]


@router.post(
    "",
    response_model=CostCenterRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_role([UserRole.ADMIN, UserRole.ACCOUNTANT]))],
)
def create_cost_center(
    payload: CostCenterCreate,
    db: DbSession,
    service: CostCenterServiceDep,
) -> CostCenterRead:
    """Crea un centro de costo; el código debe ser único."""
    with operation_transaction(db):
        center = service.create(
            code=payload.code,
            name=payload.name,
            description=payload.description,
        )
    return CostCenterRead.model_validate(center)


@router.get(
    "/{cost_center_id}",
    response_model=CostCenterRead,
    dependencies=[Depends(require_role([UserRole.ADMIN, UserRole.ACCOUNTANT, UserRole.CASHIER]))],
)
def get_cost_center(
    cost_center_id: UUID,
    service: CostCenterServiceDep,
) -> CostCenterRead:
    """Obtiene un centro de costo por identificador."""
    return CostCenterRead.model_validate(service.get(cost_center_id))


@router.patch(
    "/{cost_center_id}",
    response_model=CostCenterRead,
    dependencies=[Depends(require_role([UserRole.ADMIN, UserRole.ACCOUNTANT]))],
)
def update_cost_center(
    cost_center_id: UUID,
    payload: CostCenterUpdate,
    db: DbSession,
    service: CostCenterServiceDep,
) -> CostCenterRead:
    """Actualiza un centro de costo (ADMIN, ACCOUNTANT)."""
    with operation_transaction(db):
        center = service.update(
            cost_center_id,
            payload.model_dump(exclude_unset=True),
        )
    return CostCenterRead.model_validate(center)


@router.delete(
    "/{cost_center_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_role([UserRole.ADMIN]))],
)
def delete_cost_center(
    cost_center_id: UUID,
    db: DbSession,
    service: CostCenterServiceDep,
) -> Response:
    """Elimina un centro de costo (ADMIN).

    Si el centro está referenciado por presupuestos, asientos o documentos,
    se desactiva (soft delete) para preservar la trazabilidad contable.
    """
    with operation_transaction(db):
        service.delete(cost_center_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


__all__ = ["router"]
