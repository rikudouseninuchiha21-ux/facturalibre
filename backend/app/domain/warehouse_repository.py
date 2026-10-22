"""Repositorio de bodegas."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.domain.exceptions import ResourceNotFoundError
from app.domain.models.stock import StockMovement
from app.domain.models.warehouse import Warehouse

DEFAULT_WAREHOUSE_CODE = "PRINCIPAL"


class WarehouseRepository:
    """Acceso a datos de bodegas."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, values: dict[str, Any]) -> Warehouse:
        """Crea una bodega y confirma la transacción."""
        warehouse = Warehouse(**values)
        self.db.add(warehouse)
        self.db.commit()
        self.db.refresh(warehouse)
        return warehouse

    def get_by_id(self, warehouse_id: UUID) -> Warehouse | None:
        """Obtiene una bodega por id, activa o inactiva."""
        return self.db.get(Warehouse, warehouse_id)

    def list(
        self,
        *,
        limit: int,
        offset: int,
        is_active: bool | None = None,
    ) -> list[Warehouse]:
        """Lista bodegas con filtro opcional por estado."""
        statement = select(Warehouse)
        if is_active is not None:
            statement = statement.where(Warehouse.is_active.is_(is_active))
        statement = (
            statement.order_by(Warehouse.created_at.desc(), Warehouse.id)
            .limit(limit)
            .offset(offset)
        )
        return list(self.db.scalars(statement).all())

    def update(self, warehouse_id: UUID, values: dict[str, Any]) -> Warehouse:
        """Actualiza campos editables y confirma la transacción."""
        warehouse = self.get_by_id(warehouse_id)
        if warehouse is None:
            raise ResourceNotFoundError("Bodega no encontrada")
        for field, value in values.items():
            setattr(warehouse, field, value)
        self.db.commit()
        self.db.refresh(warehouse)
        return warehouse

    def deactivate(self, warehouse_id: UUID) -> None:
        """Baja lógica: conserva la bodega y su historial."""
        warehouse = self.get_by_id(warehouse_id)
        if warehouse is None:
            raise ResourceNotFoundError("Bodega no encontrada")
        if warehouse.is_active:
            warehouse.is_active = False
            self.db.commit()

    def get_default_active_id(self) -> UUID | None:
        """Devuelve la bodega activa usada por la emisión de facturas.

        Se prefiere el código ``PRINCIPAL``. Si no existe, se usa la bodega
        activa más antigua para que el MVP sea determinista.

        REQUIERE VALIDACIÓN: la bodega de despacho debería seleccionarse en la
        factura o configurarse por terminal/POS en una fase posterior.
        """
        preferred = self.db.scalar(
            select(Warehouse.id)
            .where(
                Warehouse.is_active.is_(True),
                func.lower(Warehouse.code) == DEFAULT_WAREHOUSE_CODE.lower(),
            )
            .order_by(Warehouse.created_at, Warehouse.id)
            .limit(1)
        )
        if preferred is not None:
            return preferred

        return self.db.scalar(
            select(Warehouse.id)
            .where(Warehouse.is_active.is_(True))
            .order_by(Warehouse.created_at, Warehouse.id)
            .limit(1)
        )

    def has_movements(self, warehouse_id: UUID) -> bool:
        """Indica si la bodega tiene movimientos y por tanto historial."""
        return (
            self.db.scalar(
                select(StockMovement.id).where(StockMovement.warehouse_id == warehouse_id).limit(1)
            )
            is not None
        )

    def rollback(self) -> None:
        """Revierte la transacción en curso tras un error de integridad."""
        self.db.rollback()
