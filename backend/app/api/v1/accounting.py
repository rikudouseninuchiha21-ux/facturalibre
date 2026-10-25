"""Endpoints de consulta del catálogo PUC y de los asientos contables."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.dependencies.auth import get_current_user, require_role
from app.application.accounting.period_service import FiscalPeriodService
from app.application.accounting.schemas import (
    AccountingAccountRead,
    AccountingEntryRead,
    ClosePeriodRequest,
    FiscalPeriodRead,
)
from app.domain.accounting_repository import AccountingRepository
from app.domain.exceptions import ResourceNotFoundError
from app.domain.models.auth import UserRole
from app.infrastructure.database import get_db
from app.infrastructure.transactions import operation_transaction

router = APIRouter(
    prefix="/accounting",
    tags=["accounting"],
    dependencies=[
        Depends(get_current_user),
        Depends(require_role([UserRole.ADMIN])),
    ],
)

DbSession = Annotated[Session, Depends(get_db)]


def get_accounting_repository(db: DbSession) -> AccountingRepository:
    """Construye el repositorio contable con la sesión de la petición."""
    return AccountingRepository(db)


AccountingRepositoryDep = Annotated[AccountingRepository, Depends(get_accounting_repository)]


def get_fiscal_period_service(db: DbSession) -> FiscalPeriodService:
    """Construye el servicio de cierre de periodos."""
    return FiscalPeriodService(db)


FiscalPeriodServiceDep = Annotated[FiscalPeriodService, Depends(get_fiscal_period_service)]


@router.post("/close-period", response_model=FiscalPeriodRead)
def close_period(
    payload: ClosePeriodRequest,
    db: DbSession,
    service: FiscalPeriodServiceDep,
) -> FiscalPeriodRead:
    """Cierra un mes contable y bloquea la creación de nuevos asientos.

    El cierre valida que no existan asientos descuadrados y se ejecuta en una
    transacción atómica con ``operation_transaction``.
    """
    with operation_transaction(db):
        period = service.close_period(year=payload.year, month=payload.month)
    return FiscalPeriodRead.model_validate(period)


@router.get("/accounts", response_model=list[AccountingAccountRead])
def list_accounts(
    repository: AccountingRepositoryDep,
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[AccountingAccountRead]:
    """Lista el catálogo PUC ordenado por código."""
    accounts = repository.list_accounts(limit=limit, offset=offset)
    return [AccountingAccountRead.model_validate(account) for account in accounts]


@router.get("/entries", response_model=list[AccountingEntryRead])
def list_entries(
    repository: AccountingRepositoryDep,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[AccountingEntryRead]:
    """Lista los asientos contables con sus movimientos."""
    entries = repository.list_entries(limit=limit, offset=offset)
    return [AccountingEntryRead.model_validate(entry) for entry in entries]


@router.get("/entries/{entry_id}", response_model=AccountingEntryRead)
def get_entry(
    entry_id: UUID,
    repository: AccountingRepositoryDep,
) -> AccountingEntryRead:
    """Obtiene el detalle de un asiento contable."""
    entry = repository.get_entry(entry_id)
    if entry is None:
        raise ResourceNotFoundError("Asiento contable no encontrado")
    return AccountingEntryRead.model_validate(entry)
