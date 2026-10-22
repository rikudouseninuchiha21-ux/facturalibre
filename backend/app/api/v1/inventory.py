"""Rutas de movimientos y saldos de inventario."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.application.inventory.schemas import (
    StockBalanceRead,
    StockMovementCreate,
    StockMovementRead,
)
from app.application.inventory.service import InventoryService
from app.domain.inventory_repository import InventoryRepository
from app.infrastructure.database import get_db
from app.infrastructure.transactions import operation_transaction

router = APIRouter(prefix="/inventory", tags=["inventory"])

DbSession = Annotated[Session, Depends(get_db)]


def get_inventory_repository(db: DbSession) -> InventoryRepository:
    """Construye el repositorio con la sesión de la petición."""
    return InventoryRepository(db)


InventoryRepositoryDep = Annotated[InventoryRepository, Depends(get_inventory_repository)]


@router.post(
    "/movements",
    response_model=StockMovementRead,
    status_code=status.HTTP_201_CREATED,
)
def register_movement(
    payload: StockMovementCreate,
    db: DbSession,
) -> StockMovementRead:
    """Registra una entrada, salida o ajuste y actualiza el saldo."""
    with operation_transaction(db):
        movement = InventoryService(db).register_movement(
            item_id=payload.item_id,
            warehouse_id=payload.warehouse_id,
            movement_type=payload.movement_type,
            quantity=payload.quantity,
            unit_cost=payload.unit_cost,
            reference=payload.reference,
        )
    return StockMovementRead.model_validate(movement)


@router.get("/movements", response_model=list[StockMovementRead])
def list_movements(
    repository: InventoryRepositoryDep,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
    warehouse_id: UUID | None = None,
    item_id: UUID | None = None,
) -> list[StockMovementRead]:
    """Lista movimientos con filtros opcionales por bodega e ítem."""
    movements = repository.list_movements(
        limit=limit,
        offset=offset,
        warehouse_id=warehouse_id,
        item_id=item_id,
    )
    return [StockMovementRead.model_validate(movement) for movement in movements]


@router.get("/balances", response_model=list[StockBalanceRead])
def list_balances(
    repository: InventoryRepositoryDep,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
    warehouse_id: UUID | None = None,
    item_id: UUID | None = None,
) -> list[StockBalanceRead]:
    """Consulta el stock actual, filtrable por bodega e ítem."""
    balances = repository.list_balances(
        limit=limit,
        offset=offset,
        warehouse_id=warehouse_id,
        item_id=item_id,
    )
    return [StockBalanceRead.model_validate(balance) for balance in balances]
