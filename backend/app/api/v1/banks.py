"""Endpoints de conciliación bancaria.

Se expone un namespace ``/banks`` para las operaciones de conciliación, sin
duplicar el CRUD de tesorería que vive en ``/treasury/accounts``.
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.dependencies.auth import get_current_user, require_role
from app.application.reconciliation_schemas import (
    ReconciliationCandidatesResponse,
    ReconciliationRequest,
    ReconciliationResult,
)
from app.application.reconciliation_service import ReconciliationService
from app.domain.models.auth import UserRole
from app.infrastructure.database import get_db
from app.infrastructure.transactions import operation_transaction

router = APIRouter(
    prefix="/banks",
    tags=["banks"],
    dependencies=[
        Depends(get_current_user),
        Depends(require_role([UserRole.ADMIN, UserRole.ACCOUNTANT])),
    ],
)

DbSession = Annotated[Session, Depends(get_db)]


def get_reconciliation_service(db: DbSession) -> ReconciliationService:
    """Construye el servicio de conciliación con la sesión de la petición."""
    return ReconciliationService(db)


ReconciliationServiceDep = Annotated[
    ReconciliationService, Depends(get_reconciliation_service)
]


@router.get(
    "/{account_id}/reconciliation-candidates",
    response_model=ReconciliationCandidatesResponse,
)
def get_reconciliation_candidates(
    account_id: UUID,
    service: ReconciliationServiceDep,
) -> ReconciliationCandidatesResponse:
    """Lista movimientos pendientes y sus pagos/gastos candidatos."""
    return service.candidates(account_id)


@router.post(
    "/{account_id}/reconcile",
    response_model=ReconciliationResult,
)
def reconcile_bank_movement(
    account_id: UUID,
    payload: ReconciliationRequest,
    db: DbSession,
    service: ReconciliationServiceDep,
) -> ReconciliationResult:
    """Vincula un pago/gasto con un movimiento y marca la conciliación."""
    with operation_transaction(db):
        result = service.reconcile(account_id, payload)
    return result


__all__ = ["router"]
