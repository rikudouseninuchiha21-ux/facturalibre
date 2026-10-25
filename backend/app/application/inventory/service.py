"""Servicio de inventario: movimientos y actualización transaccional de saldos.

El servicio no hace commit. La API o el caso de uso que lo invoca controla la
transacción, igual que ``AccountingService``, para que factura, stock y
contabilidad se confirmen o reviertan juntos.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy.orm import Session

from app.domain.exceptions import (
    InsufficientStockError,
    InventoryError,
    ResourceNotFoundError,
)
from app.domain.inventory_repository import InventoryRepository
from app.domain.item_repository import ItemRepository
from app.domain.models.stock import StockMovement, StockMovementType
from app.domain.warehouse_repository import WarehouseRepository

if TYPE_CHECKING:
    from app.domain.models.invoice import Invoice

INCREASE_TYPES = frozenset(
    {
        StockMovementType.IN,
        StockMovementType.TRANSFER_IN,
        StockMovementType.ADJUSTMENT,
    }
)
DECREASE_TYPES = frozenset(
    {
        StockMovementType.OUT,
        StockMovementType.TRANSFER_OUT,
    }
)


class InventoryService:
    """Registra movimientos y mantiene el saldo por ítem y bodega."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.repository = InventoryRepository(db)
        self.items = ItemRepository(db)
        self.warehouses = WarehouseRepository(db)

    def register_movement(
        self,
        *,
        item_id: UUID,
        warehouse_id: UUID,
        movement_type: StockMovementType,
        quantity: Decimal,
        unit_cost: Decimal | None = None,
        reference: str | None = None,
    ) -> StockMovement:
        """Registra un movimiento y actualiza el saldo en la misma transacción.

        Los tipos de entrada incrementan; las salidas validan stock suficiente y
        decrementan. Si la validación falla no se persiste ningún cambio.
        """
        if quantity <= 0:
            raise InventoryError("La cantidad del movimiento debe ser mayor que cero")
        if unit_cost is not None and unit_cost < 0:
            raise InventoryError("El costo unitario no puede ser negativo")
        if movement_type not in INCREASE_TYPES | DECREASE_TYPES:
            raise InventoryError(f"Tipo de movimiento no soportado: {movement_type}")

        if self.items.get_by_id(item_id) is None:
            raise ResourceNotFoundError("Ítem no encontrado")

        warehouse = self.warehouses.get_by_id(warehouse_id)
        if warehouse is None:
            raise ResourceNotFoundError("Bodega no encontrada")
        if not warehouse.is_active:
            raise InventoryError("La bodega está inactiva")

        self.repository.ensure_balance(item_id, warehouse_id)
        balance = self.repository.get_balance_for_update(item_id, warehouse_id)
        if balance is None:
            raise RuntimeError("No se pudo crear el saldo de inventario")

        if movement_type in DECREASE_TYPES and balance.quantity < quantity:
            item = self.items.get_by_id(item_id)
            warehouse = self.warehouses.get_by_id(warehouse_id)
            item_name = item.name if item else str(item_id)
            warehouse_name = warehouse.name if warehouse else str(warehouse_id)
            raise InsufficientStockError(
                f"Stock insuficiente para '{item_name}' en '{warehouse_name}': "
                f"disponible {balance.quantity}, solicitado {quantity}."
            )

        # Las salidas sin costo explícito se valorizan con el promedio
        # ponderado disponible. El saldo ya está bloqueado, de modo que la
        # valorización y el descuento de unidades son consistentes entre sí.
        if unit_cost is None and movement_type in DECREASE_TYPES:
            unit_cost = self.repository.get_weighted_average_cost(
                item_id,
                warehouse_id,
                quantity_on_hand=balance.quantity,
            )

        if movement_type in INCREASE_TYPES:
            balance.quantity += quantity
        else:
            balance.quantity -= quantity
        balance.updated_at = datetime.now(UTC)

        movement = StockMovement(
            item_id=item_id,
            warehouse_id=warehouse_id,
            movement_type=movement_type,
            quantity=quantity,
            unit_cost=unit_cost,
            reference=reference,
        )
        return self.repository.add_movement(movement)

    def register_invoice_issue(self, invoice: Invoice) -> list[StockMovement]:
        """Genera una salida por cada línea de una factura emitida.

        La bodega se resuelve con la política de ``WarehouseRepository``:
        primero ``PRINCIPAL`` y luego la bodega activa más antigua.

        REQUIERE VALIDACIÓN: el MVP asume que todo ítem es inventariable y que
        la factura no elige bodega. Ambos supuestos deben revisarse cuando se
        incorporen servicios y despacho multi-bodega.
        """
        warehouse_id = self.warehouses.get_default_active_id()
        if warehouse_id is None:
            raise InventoryError("No hay una bodega activa configurada para descontar inventario")

        movements: list[StockMovement] = []
        reference = invoice.number or str(invoice.id)
        for line in invoice.lines:
            if line.item_id is None:
                continue
            movements.append(
                self.register_movement(
                    item_id=line.item_id,
                    warehouse_id=warehouse_id,
                    movement_type=StockMovementType.OUT,
                    quantity=line.quantity,
                    reference=reference,
                )
            )
        return movements
