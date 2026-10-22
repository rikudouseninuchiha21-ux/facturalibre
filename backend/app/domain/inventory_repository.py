"""Acceso a datos del libro de movimientos y de los saldos de inventario."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session, joinedload

from app.domain.models.stock import StockBalance, StockMovement


class InventoryRepository:
    """Consultas y persistencia del inventario.

    No hace commit: el servicio y la capa de API controlan la transacción para
    que el movimiento, el saldo y cualquier efecto de facturación sean atómicos.
    """

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_balance_for_update(
        self,
        item_id: UUID,
        warehouse_id: UUID,
    ) -> StockBalance | None:
        """Bloquea la fila de saldo para evitar actualizaciones perdidas."""
        statement = (
            select(StockBalance)
            .where(
                StockBalance.item_id == item_id,
                StockBalance.warehouse_id == warehouse_id,
            )
            .with_for_update()
        )
        return self.db.scalar(statement)

    def ensure_balance(self, item_id: UUID, warehouse_id: UUID) -> None:
        """Crea la fila de saldo en cero si todavía no existe.

        ``ON CONFLICT DO NOTHING`` evita que dos primeras entradas concurrentes
        choquen por la PK compuesta.
        """
        statement = (
            pg_insert(StockBalance)
            .values(item_id=item_id, warehouse_id=warehouse_id, quantity=0)
            .on_conflict_do_nothing(
                index_elements=[StockBalance.item_id, StockBalance.warehouse_id]
            )
        )
        self.db.execute(statement)

    def add_movement(self, movement: StockMovement) -> StockMovement:
        """Persiste un movimiento sin confirmar la transacción."""
        self.db.add(movement)
        self.db.flush()
        self.db.refresh(movement)
        return movement

    def list_balances(
        self,
        *,
        limit: int,
        offset: int,
        warehouse_id: UUID | None = None,
        item_id: UUID | None = None,
    ) -> list[StockBalance]:
        """Lista saldos con nombres de ítem y bodega precargados."""
        statement = select(StockBalance).options(
            joinedload(StockBalance.item),
            joinedload(StockBalance.warehouse),
        )
        if warehouse_id is not None:
            statement = statement.where(StockBalance.warehouse_id == warehouse_id)
        if item_id is not None:
            statement = statement.where(StockBalance.item_id == item_id)
        statement = (
            statement.order_by(
                StockBalance.warehouse_id,
                StockBalance.item_id,
            )
            .limit(limit)
            .offset(offset)
        )
        return list(self.db.scalars(statement).all())

    def list_movements(
        self,
        *,
        limit: int,
        offset: int,
        warehouse_id: UUID | None = None,
        item_id: UUID | None = None,
    ) -> list[StockMovement]:
        """Lista movimientos del más reciente al más antiguo."""
        statement = select(StockMovement)
        if warehouse_id is not None:
            statement = statement.where(StockMovement.warehouse_id == warehouse_id)
        if item_id is not None:
            statement = statement.where(StockMovement.item_id == item_id)
        statement = (
            statement.order_by(
                StockMovement.created_at.desc(),
                StockMovement.id,
            )
            .limit(limit)
            .offset(offset)
        )
        return list(self.db.scalars(statement).all())
