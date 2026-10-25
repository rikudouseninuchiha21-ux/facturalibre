"""Lógica de negocio de centros de costo.

El servicio no hace commit. La API controla la transacción vía
``operation_transaction``.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.domain.cost_center_repository import CostCenterRepository
from app.domain.exceptions import CostCenterError, ResourceNotFoundError
from app.domain.models.budgeting import CostCenter


class CostCenterService:
    """CRUD de centros de costo con eliminación condicionada."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.centers = CostCenterRepository(db)

    def create(
        self,
        *,
        code: str,
        name: str,
        description: str | None = None,
    ) -> CostCenter:
        """Crea un centro de costo; el código debe ser único."""
        if self.centers.get_by_code(code) is not None:
            raise CostCenterError(f"Ya existe un centro de costo con el código {code}")
        return self.centers.create({"code": code, "name": name, "description": description})

    def get(self, cost_center_id: UUID) -> CostCenter:
        center = self.centers.get_by_id(cost_center_id)
        if center is None:
            raise ResourceNotFoundError("Centro de costo no encontrado")
        return center

    def list(
        self,
        *,
        include_inactive: bool = False,
        limit: int = 100,
        offset: int = 0,
    ) -> list[CostCenter]:
        return self.centers.list(
            include_inactive=include_inactive,
            limit=limit,
            offset=offset,
        )

    def update(self, cost_center_id: UUID, values: dict[str, Any]) -> CostCenter:
        """Aplica cambios parciales; valida unicidad si cambia el código."""
        center = self.get(cost_center_id)
        new_code = values.get("code")
        if new_code is not None and new_code != center.code:
            existing = self.centers.get_by_code(new_code)
            if existing is not None and existing.id != center.id:
                raise CostCenterError(f"Ya existe un centro de costo con el código {new_code}")
        changes = {k: v for k, v in values.items() if v is not None or k == "is_active"}
        return self.centers.update(center, changes)

    def delete(self, cost_center_id: UUID) -> None:
        """Elimina el centro de costo.

        Si el centro está referenciado por presupuestos, asientos o documentos,
        se desactiva (soft delete) para preservar la integridad referencial y
        la trazabilidad contable. Solo se elimina físicamente cuando no existe
        ninguna referencia.
        """
        center = self.get(cost_center_id)
        if self.centers.is_referenced(cost_center_id):
            self.centers.update(center, {"is_active": False})
            return
        self.centers.delete(center)


__all__ = ["CostCenterService"]
