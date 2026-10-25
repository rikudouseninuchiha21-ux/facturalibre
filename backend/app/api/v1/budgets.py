"""Rutas de presupuestos mensuales por centro de costo."""

from __future__ import annotations

from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.api.dependencies.auth import get_current_user, require_role
from app.application.budget_actuals_service import BudgetActualsService
from app.application.budget_schemas import (
    BudgetAlertItem,
    BudgetCreate,
    BudgetLineCreate,
    BudgetLineRead,
    BudgetLineUpdate,
    BudgetRead,
    BudgetUpdate,
    BudgetVsActualResponse,
)
from app.application.budget_service import BudgetService
from app.domain.models.auth import UserRole
from app.domain.models.budgeting import BudgetStatus
from app.infrastructure.database import get_db
from app.infrastructure.transactions import operation_transaction

router = APIRouter(
    prefix="/budgets",
    tags=["budgets"],
    dependencies=[Depends(get_current_user)],
)

DbSession = Annotated[Session, Depends(get_db)]

# Roles que pueden ver presupuestos y su comparación contra el real.
READ_ROLES = [UserRole.ADMIN, UserRole.ACCOUNTANT]
WRITE_ROLES = [UserRole.ADMIN, UserRole.ACCOUNTANT]


def get_budget_service(db: DbSession) -> BudgetService:
    """Construye el servicio de presupuestos con la sesión de la petición."""
    return BudgetService(db)


BudgetServiceDep = Annotated[BudgetService, Depends(get_budget_service)]


def get_budget_actuals_service(db: DbSession) -> BudgetActualsService:
    """Construye el servicio del reporte Presupuesto vs Real."""
    return BudgetActualsService(db)


BudgetActualsServiceDep = Annotated[BudgetActualsService, Depends(get_budget_actuals_service)]


@router.get(
    "",
    response_model=list[BudgetRead],
    dependencies=[Depends(require_role(READ_ROLES))],
)
def list_budgets(
    service: BudgetServiceDep,
    cost_center_id: Annotated[UUID | None, Query()] = None,
    period_year: Annotated[int | None, Query(ge=2000, le=2100)] = None,
    period_month: Annotated[int | None, Query(ge=1, le=12)] = None,
    status: Annotated[BudgetStatus | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[BudgetRead]:
    """Lista presupuestos con filtros por centro, periodo y estado."""
    budgets = service.list(
        cost_center_id=cost_center_id,
        period_year=period_year,
        period_month=period_month,
        status=status,
        limit=limit,
        offset=offset,
    )
    return [BudgetRead.model_validate(budget) for budget in budgets]


@router.get(
    "/alerts",
    response_model=list[BudgetAlertItem],
    dependencies=[Depends(require_role(READ_ROLES))],
)
def get_budget_alerts(
    actuals: BudgetActualsServiceDep,
    period_year: Annotated[int, Query(ge=2000, le=2100)],
    period_month: Annotated[int, Query(ge=1, le=12)],
    level: Annotated[Literal["WARNING", "CRITICAL", "OVER"] | None, Query()] = None,
) -> list[BudgetAlertItem]:
    """Presupuestos del periodo con su nivel de alerta de sobregiro.

    Solo incluye presupuestos APPROVED o CLOSED, ordenados por utilización
    descendente. ``level`` filtra por WARNING, CRITICAL u OVER.
    """
    return actuals.alerts(
        period_year=period_year,
        period_month=period_month,
        level=level,
    )


@router.post(
    "",
    response_model=BudgetRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_role(WRITE_ROLES))],
)
def create_budget(
    payload: BudgetCreate,
    db: DbSession,
    service: BudgetServiceDep,
) -> BudgetRead:
    """Abre un presupuesto mensual en estado DRAFT."""
    with operation_transaction(db):
        budget = service.create(
            cost_center_id=payload.cost_center_id,
            period_year=payload.period_year,
            period_month=payload.period_month,
            name=payload.name,
            notes=payload.notes,
        )
    return BudgetRead.model_validate(service.get(budget.id))


@router.get(
    "/{budget_id}",
    response_model=BudgetRead,
    dependencies=[Depends(require_role(READ_ROLES))],
)
def get_budget(
    budget_id: UUID,
    service: BudgetServiceDep,
) -> BudgetRead:
    """Obtiene un presupuesto con su centro de costo y sus líneas."""
    return BudgetRead.model_validate(service.get(budget_id))


@router.patch(
    "/{budget_id}",
    response_model=BudgetRead,
    dependencies=[Depends(require_role(WRITE_ROLES))],
)
def update_budget(
    budget_id: UUID,
    payload: BudgetUpdate,
    db: DbSession,
    service: BudgetServiceDep,
) -> BudgetRead:
    """Actualiza la cabecera del presupuesto; solo en DRAFT."""
    with operation_transaction(db):
        service.update(budget_id, payload.model_dump(exclude_unset=True))
    return BudgetRead.model_validate(service.get(budget_id))


@router.delete(
    "/{budget_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_role([UserRole.ADMIN]))],
)
def delete_budget(
    budget_id: UUID,
    db: DbSession,
    service: BudgetServiceDep,
) -> Response:
    """Elimina el presupuesto con sus líneas; solo en DRAFT (ADMIN)."""
    with operation_transaction(db):
        service.delete(budget_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/{budget_id}/lines",
    response_model=BudgetLineRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_role(WRITE_ROLES))],
)
def add_budget_line(
    budget_id: UUID,
    payload: BudgetLineCreate,
    db: DbSession,
    service: BudgetServiceDep,
) -> BudgetLineRead:
    """Agrega una cuenta PUC presupuestada; solo en DRAFT."""
    with operation_transaction(db):
        line = service.add_line(
            budget_id,
            account_code=payload.account_code,
            amount=payload.amount,
            notes=payload.notes,
        )
    return BudgetLineRead.model_validate(line)


@router.patch(
    "/{budget_id}/lines/{line_id}",
    response_model=BudgetLineRead,
    dependencies=[Depends(require_role(WRITE_ROLES))],
)
def update_budget_line(
    budget_id: UUID,
    line_id: UUID,
    payload: BudgetLineUpdate,
    db: DbSession,
    service: BudgetServiceDep,
) -> BudgetLineRead:
    """Actualiza el monto o las notas de una línea; solo en DRAFT."""
    with operation_transaction(db):
        line = service.update_line(budget_id, line_id, payload.model_dump(exclude_unset=True))
    return BudgetLineRead.model_validate(line)


@router.delete(
    "/{budget_id}/lines/{line_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_role(WRITE_ROLES))],
)
def delete_budget_line(
    budget_id: UUID,
    line_id: UUID,
    db: DbSession,
    service: BudgetServiceDep,
) -> Response:
    """Quita una cuenta del presupuesto; solo en DRAFT."""
    with operation_transaction(db):
        service.remove_line(budget_id, line_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/{budget_id}/approve",
    response_model=BudgetRead,
    dependencies=[Depends(require_role(WRITE_ROLES))],
)
def approve_budget(
    budget_id: UUID,
    db: DbSession,
    service: BudgetServiceDep,
) -> BudgetRead:
    """Aprueba el presupuesto: DRAFT → APPROVED; exige líneas y total > 0."""
    with operation_transaction(db):
        service.approve(budget_id)
    return BudgetRead.model_validate(service.get(budget_id))


@router.post(
    "/{budget_id}/close",
    response_model=BudgetRead,
    dependencies=[Depends(require_role([UserRole.ADMIN]))],
)
def close_budget(
    budget_id: UUID,
    db: DbSession,
    service: BudgetServiceDep,
) -> BudgetRead:
    """Cierra el presupuesto aprobado: queda inmutable (ADMIN)."""
    with operation_transaction(db):
        service.close(budget_id)
    return BudgetRead.model_validate(service.get(budget_id))


@router.get(
    "/{budget_id}/actuals",
    response_model=BudgetVsActualResponse,
    dependencies=[Depends(require_role(READ_ROLES))],
)
def get_budget_actuals(
    budget_id: UUID,
    actuals: BudgetActualsServiceDep,
) -> BudgetVsActualResponse:
    """Compara el presupuesto contra el gasto real del mes."""
    return actuals.report(budget_id)


__all__ = ["router"]
