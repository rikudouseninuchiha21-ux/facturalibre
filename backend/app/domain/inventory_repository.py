"""Acceso a datos del libro de movimientos y de los saldos de inventario."""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session, joinedload

from app.domain.models.stock import StockBalance, StockMovement, StockMovementType
from app.infrastructure.tenancy import require_company_id

COST_PRECISION = Decimal("0.0001")
INCREASE_TYPES = (
    StockMovementType.IN,
    StockMovementType.TRANSFER_IN,
    StockMovementType.ADJUSTMENT,
)
DECREASE_TYPES = (
    StockMovementType.OUT,
    StockMovementType.TRANSFER_OUT,
)


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
            .values(
                company_id=require_company_id(self.db),
                item_id=item_id,
                warehouse_id=warehouse_id,
                quantity=0,
            )
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

    def get_weighted_average_cost(
        self,
        item_id: UUID,
        warehouse_id: UUID,
        *,
        quantity_on_hand: Decimal,
    ) -> Decimal | None:
        """Calcula el costo promedio ponderado del inventario disponible.

        Solo se consideran movimientos con ``unit_cost`` conocido. El valor
        disponible es el valor de las entradas costeadas menos el de las salidas
        ya costeadas. El denominador es la cantidad total en existencia, de modo
        que el stock histórico sin costo se trata como costo cero y nunca se
        acredita a inventario más valor del que realmente se registró.

        Devuelve ``None`` cuando no hay valor o unidades disponibles. El método
        no hace commit y debe invocarse dentro de la transacción de inventario,
        después de bloquear el saldo del ítem/bodega.
        """
        incoming_statement = select(
            func.coalesce(func.sum(StockMovement.quantity * StockMovement.unit_cost), 0),
        ).where(
            StockMovement.item_id == item_id,
            StockMovement.warehouse_id == warehouse_id,
            StockMovement.movement_type.in_(INCREASE_TYPES),
            StockMovement.unit_cost.is_not(None),
        )
        outgoing_statement = select(
            func.coalesce(func.sum(StockMovement.quantity * StockMovement.unit_cost), 0),
        ).where(
            StockMovement.item_id == item_id,
            StockMovement.warehouse_id == warehouse_id,
            StockMovement.movement_type.in_(DECREASE_TYPES),
            StockMovement.unit_cost.is_not(None),
        )

        incoming_value = self.db.execute(incoming_statement).scalar_one()
        outgoing_value = self.db.execute(outgoing_statement).scalar_one()
        available_value = Decimal(str(incoming_value)) - Decimal(str(outgoing_value))
        if quantity_on_hand <= 0 or available_value <= 0:
            return None

        return (available_value / quantity_on_hand).quantize(
            COST_PRECISION,
            rounding=ROUND_HALF_UP,
        )

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
