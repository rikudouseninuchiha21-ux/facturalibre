"""Rutas del CRM: embudo Kanban, oportunidades y actividades."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.dependencies.auth import CurrentUser, get_current_user, require_role
from app.application.crm_schemas import (
    CrmActivityCreate,
    CrmActivityRead,
    CrmMoveRequest,
    CrmOpportunityCreate,
    CrmOpportunityDetailRead,
    CrmOpportunityRead,
    CrmOpportunityUpdate,
    CrmStageCreate,
    CrmStageRead,
    CrmStageUpdate,
)
from app.application.crm_service import CrmService
from app.domain.exceptions import (
    CrmStateError,
    CrmValidationError,
    ResourceNotFoundError,
)
from app.domain.models.auth import UserRole
from app.infrastructure.database import get_db
from app.infrastructure.transactions import operation_transaction

router = APIRouter(
    prefix="/crm",
    tags=["crm"],
    dependencies=[
        Depends(get_current_user),
        Depends(require_role([UserRole.ADMIN, UserRole.ACCOUNTANT, UserRole.CASHIER])),
    ],
)

DbSession = Annotated[Session, Depends(get_db)]
ADMIN_ONLY = [Depends(require_role([UserRole.ADMIN]))]


def get_crm_service(db: DbSession) -> CrmService:
    """Construye el servicio CRM."""
    return CrmService(db)


CrmServiceDep = Annotated[CrmService, Depends(get_crm_service)]


def _not_found(exc: ResourceNotFoundError) -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


def _validation(exc: CrmValidationError) -> HTTPException:
    return HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))


@router.get("/stages", response_model=list[CrmStageRead])
def list_stages(service: CrmServiceDep) -> list[CrmStageRead]:
    """Lista las etapas del embudo de la empresa activa."""
    return [CrmStageRead.model_validate(stage) for stage in service.list_stages()]


@router.post(
    "/stages",
    response_model=CrmStageRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=ADMIN_ONLY,
)
def create_stage(
    payload: CrmStageCreate,
    db: DbSession,
    service: CrmServiceDep,
) -> CrmStageRead:
    """Crea una etapa del embudo (solo ADMIN)."""
    with operation_transaction(db):
        stage = service.create_stage(payload)
    return CrmStageRead.model_validate(stage)


@router.patch(
    "/stages/{stage_id}",
    response_model=CrmStageRead,
    dependencies=ADMIN_ONLY,
)
def update_stage(
    stage_id: UUID,
    payload: CrmStageUpdate,
    db: DbSession,
    service: CrmServiceDep,
) -> CrmStageRead:
    """Actualiza una etapa del embudo (solo ADMIN)."""
    try:
        with operation_transaction(db):
            stage = service.update_stage(stage_id, payload)
    except ResourceNotFoundError as exc:
        raise _not_found(exc) from exc
    return CrmStageRead.model_validate(stage)


@router.delete(
    "/stages/{stage_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=ADMIN_ONLY,
)
def delete_stage(
    stage_id: UUID,
    db: DbSession,
    service: CrmServiceDep,
) -> Response:
    """Elimina una etapa sin oportunidades asociadas (solo ADMIN)."""
    try:
        with operation_transaction(db):
            service.delete_stage(stage_id)
    except ResourceNotFoundError as exc:
        raise _not_found(exc) from exc
    except IntegrityError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No se puede eliminar una etapa con oportunidades asociadas",
        ) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/opportunities", response_model=list[CrmOpportunityRead])
def list_opportunities(
    service: CrmServiceDep,
    stage_id: UUID | None = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 200,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[CrmOpportunityRead]:
    """Lista oportunidades para el tablero Kanban."""
    opportunities = service.list_opportunities(
        stage_id=stage_id,
        limit=limit,
        offset=offset,
    )
    return [CrmOpportunityRead.model_validate(item) for item in opportunities]


@router.post(
    "/opportunities",
    response_model=CrmOpportunityRead,
    status_code=status.HTTP_201_CREATED,
)
def create_opportunity(
    payload: CrmOpportunityCreate,
    current_user: CurrentUser,
    db: DbSession,
    service: CrmServiceDep,
) -> CrmOpportunityRead:
    """Crea una oportunidad en la empresa activa."""
    owner_id = payload.owner_id or current_user.id
    try:
        with operation_transaction(db):
            opportunity = service.create_opportunity(payload, owner_id=owner_id)
    except CrmValidationError as exc:
        raise _validation(exc) from exc
    return CrmOpportunityRead.model_validate(opportunity)


@router.get(
    "/opportunities/{opportunity_id}",
    response_model=CrmOpportunityDetailRead,
)
def get_opportunity(
    opportunity_id: UUID,
    service: CrmServiceDep,
) -> CrmOpportunityDetailRead:
    """Obtiene una oportunidad con su historial de actividades."""
    try:
        opportunity = service.get_opportunity(opportunity_id, with_activities=True)
    except ResourceNotFoundError as exc:
        raise _not_found(exc) from exc
    return CrmOpportunityDetailRead.model_validate(opportunity)


@router.patch(
    "/opportunities/{opportunity_id}",
    response_model=CrmOpportunityRead,
)
def update_opportunity(
    opportunity_id: UUID,
    payload: CrmOpportunityUpdate,
    db: DbSession,
    service: CrmServiceDep,
) -> CrmOpportunityRead:
    """Actualiza los datos de una oportunidad."""
    try:
        with operation_transaction(db):
            opportunity = service.update_opportunity(opportunity_id, payload)
    except ResourceNotFoundError as exc:
        raise _not_found(exc) from exc
    except CrmValidationError as exc:
        raise _validation(exc) from exc
    return CrmOpportunityRead.model_validate(opportunity)


@router.patch(
    "/opportunities/{opportunity_id}/move",
    response_model=CrmOpportunityRead,
)
def move_opportunity(
    opportunity_id: UUID,
    payload: CrmMoveRequest,
    db: DbSession,
    service: CrmServiceDep,
) -> CrmOpportunityRead:
    """Mueve la oportunidad a otra etapa del Kanban."""
    try:
        with operation_transaction(db):
            opportunity = service.move_opportunity(opportunity_id, payload.stage_id)
    except ResourceNotFoundError as exc:
        raise _not_found(exc) from exc
    except CrmValidationError as exc:
        raise _validation(exc) from exc
    return CrmOpportunityRead.model_validate(opportunity)


@router.delete(
    "/opportunities/{opportunity_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_opportunity(
    opportunity_id: UUID,
    db: DbSession,
    service: CrmServiceDep,
) -> Response:
    """Elimina una oportunidad y su historial."""
    try:
        with operation_transaction(db):
            service.delete_opportunity(opportunity_id)
    except ResourceNotFoundError as exc:
        raise _not_found(exc) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/opportunities/{opportunity_id}/activities",
    response_model=list[CrmActivityRead],
)
def list_activities(
    opportunity_id: UUID,
    service: CrmServiceDep,
) -> list[CrmActivityRead]:
    """Lista el historial de actividades de una oportunidad."""
    try:
        activities = service.list_activities(opportunity_id)
    except ResourceNotFoundError as exc:
        raise _not_found(exc) from exc
    return [CrmActivityRead.model_validate(item) for item in activities]


@router.post(
    "/opportunities/{opportunity_id}/activities",
    response_model=CrmActivityRead,
    status_code=status.HTTP_201_CREATED,
)
def create_activity(
    opportunity_id: UUID,
    payload: CrmActivityCreate,
    current_user: CurrentUser,
    db: DbSession,
    service: CrmServiceDep,
) -> CrmActivityRead:
    """Registra una llamada, correo, reunión o nota."""
    try:
        with operation_transaction(db):
            activity = service.add_activity(
                opportunity_id,
                payload,
                created_by=current_user.id,
            )
    except ResourceNotFoundError as exc:
        raise _not_found(exc) from exc
    return CrmActivityRead.model_validate(activity)


@router.post(
    "/opportunities/{opportunity_id}/convert-to-quote",
    response_model=CrmOpportunityRead,
)
def convert_to_quote(
    opportunity_id: UUID,
    db: DbSession,
    service: CrmServiceDep,
) -> CrmOpportunityRead:
    """Convierte la oportunidad en un borrador de cotización."""
    try:
        with operation_transaction(db):
            opportunity = service.convert_to_quote(opportunity_id)
    except ResourceNotFoundError as exc:
        raise _not_found(exc) from exc
    except CrmStateError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    except CrmValidationError as exc:
        raise _validation(exc) from exc
    return CrmOpportunityRead.model_validate(opportunity)
