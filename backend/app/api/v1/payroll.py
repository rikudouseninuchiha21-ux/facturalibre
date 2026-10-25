"""Rutas de periodos y liquidación de nómina."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.dependencies.auth import get_current_user, require_role
from app.application.payroll.schemas import PayrollPeriodCreate, PayrollPeriodRead
from app.application.payroll.service import PayrollService
from app.domain.cost_center_repository import CostCenterRepository
from app.domain.exceptions import ResourceNotFoundError
from app.domain.models.auth import UserRole
from app.domain.payroll_repository import PayrollRepository
from app.infrastructure.database import get_db
from app.infrastructure.transactions import operation_transaction

router = APIRouter(
    prefix="/payroll",
    tags=["payroll"],
    dependencies=[
        Depends(get_current_user),
        Depends(require_role([UserRole.ADMIN])),
    ],
)

DbSession = Annotated[Session, Depends(get_db)]
PERIOD_CONFLICT = "Ya existe un periodo de nómina para ese mes y año"


def get_payroll_repository(db: DbSession) -> PayrollRepository:
    """Construye el repositorio con la sesión de la petición."""
    return PayrollRepository(db)


PayrollRepositoryDep = Annotated[PayrollRepository, Depends(get_payroll_repository)]


@router.post(
    "/periods",
    response_model=PayrollPeriodRead,
    status_code=status.HTTP_201_CREATED,
)
def create_period(
    payload: PayrollPeriodCreate,
    db: DbSession,
    repository: PayrollRepositoryDep,
) -> PayrollPeriodRead:
    """Abre un periodo mensual de nómina en estado DRAFT."""
    if payload.cost_center_id is not None:
        cost_center = CostCenterRepository(db).get_by_id(payload.cost_center_id)
        if cost_center is None or not cost_center.is_active:
            raise HTTPException(
                status_code=422,
                detail="cost_center_id no existe o está inactivo",
            )
    try:
        period = repository.create_period(payload.model_dump())
    except IntegrityError:
        repository.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=PERIOD_CONFLICT,
        ) from None
    return PayrollPeriodRead.model_validate(period)


@router.get("/periods", response_model=list[PayrollPeriodRead])
def list_periods(
    repository: PayrollRepositoryDep,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[PayrollPeriodRead]:
    """Lista los periodos de nómina con su detalle."""
    periods = repository.list(limit=limit, offset=offset)
    return [PayrollPeriodRead.model_validate(period) for period in periods]


@router.post("/periods/{period_id}/calculate", response_model=PayrollPeriodRead)
def calculate_period(
    period_id: UUID,
    db: DbSession,
) -> PayrollPeriodRead:
    """Calcula la nómina y genera el asiento contable de forma atómica."""
    with operation_transaction(db):
        period = PayrollService(db).calculate_period(period_id)
    return PayrollPeriodRead.model_validate(period)


@router.get("/periods/{period_id}", response_model=PayrollPeriodRead)
def get_period(
    period_id: UUID,
    repository: PayrollRepositoryDep,
) -> PayrollPeriodRead:
    """Consulta el detalle calculado de un periodo."""
    period = repository.get_by_id(period_id)
    if period is None:
        raise ResourceNotFoundError("Periodo de nómina no encontrado")
    return PayrollPeriodRead.model_validate(period)
