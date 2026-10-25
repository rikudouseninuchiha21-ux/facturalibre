"""Rutas de creación y consulta de gastos operativos."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.api.dependencies.auth import get_current_user, require_role
from app.application.expense_schemas import ExpenseCreate, ExpenseRead
from app.application.expense_service import ExpenseService
from app.domain.expense_repository import ExpenseRepository
from app.domain.models.auth import UserRole
from app.infrastructure.database import get_db
from app.infrastructure.transactions import operation_transaction

router = APIRouter(
    prefix="/expenses",
    tags=["expenses"],
    dependencies=[
        Depends(get_current_user),
        Depends(require_role([UserRole.ADMIN, UserRole.ACCOUNTANT, UserRole.CASHIER])),
    ],
)

DbSession = Annotated[Session, Depends(get_db)]


def get_expense_repository(db: DbSession) -> ExpenseRepository:
    """Construye el repositorio con la sesión de la petición."""
    return ExpenseRepository(db)


ExpenseRepositoryDep = Annotated[ExpenseRepository, Depends(get_expense_repository)]


def get_expense_service(db: DbSession) -> ExpenseService:
    """Construye el servicio de gastos con la sesión de la petición."""
    return ExpenseService(db)


ExpenseServiceDep = Annotated[ExpenseService, Depends(get_expense_service)]


@router.post("", response_model=ExpenseRead, status_code=status.HTTP_201_CREATED)
def create_expense(
    payload: ExpenseCreate,
    db: DbSession,
    service: ExpenseServiceDep,
) -> ExpenseRead:
    """Registra un gasto operativo y genera el asiento contable asociado.

    El asiento se genera dentro de la misma transacción: si falla la
    contabilidad, el gasto no se persiste.
    """
    with operation_transaction(db):
        expense = service.create_expense(
            date=payload.date,
            concept=payload.concept,
            amount=payload.amount,
            payment_method=payload.payment_method,
            reference=payload.reference,
            cost_center_id=payload.cost_center_id,
        )

    return ExpenseRead.model_validate(expense)


@router.get("", response_model=list[ExpenseRead])
def list_expenses(
    repository: ExpenseRepositoryDep,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[ExpenseRead]:
    """Lista gastos operativos con paginación por offset."""
    expenses = repository.list(limit=limit, offset=offset)
    return [ExpenseRead.model_validate(expense) for expense in expenses]


@router.delete("/{expense_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_expense(
    expense_id: UUID,
    db: DbSession,
    service: ExpenseServiceDep,
) -> Response:
    """Elimina lógicamente un gasto y revierte su asiento contable."""
    with operation_transaction(db):
        service.delete_expense(expense_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


__all__ = ["router"]
