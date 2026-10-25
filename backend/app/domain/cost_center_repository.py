"""Repositorio de centros de costo con SQLAlchemy 2.

El repositorio nunca confirma transacciones; la capa de API agrupa las
operaciones con ``operation_transaction``.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.models.accounting import AccountingEntryLine
from app.domain.models.budgeting import (
    Budget,
    CostCenter,
)
from app.domain.models.expense import Expense
from app.domain.models.payroll import PayrollPeriod
from app.domain.models.purchase import PurchaseInvoice


class CostCenterRepository:
    """Acceso a datos de centros de costo."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, values: dict[str, Any]) -> CostCenter:
        """Crea un centro de costo y lo persiste sin confirmar."""
        cost_center = CostCenter(**values)
        self.db.add(cost_center)
        self.db.flush()
        self.db.refresh(cost_center)
        return cost_center

    def get_by_id(self, cost_center_id: UUID) -> CostCenter | None:
        return self.db.scalar(select(CostCenter).where(CostCenter.id == cost_center_id))

    def get_by_code(self, code: str) -> CostCenter | None:
        return self.db.scalar(select(CostCenter).where(CostCenter.code == code))

    def list(
        self,
        *,
        include_inactive: bool = False,
        limit: int = 100,
        offset: int = 0,
    ) -> list[CostCenter]:
        statement = select(CostCenter).order_by(CostCenter.code)
        if not include_inactive:
            statement = statement.where(CostCenter.is_active.is_(True))
        statement = statement.limit(limit).offset(offset)
        return list(self.db.scalars(statement).all())

    def update(self, cost_center: CostCenter, values: dict[str, Any]) -> CostCenter:
        """Aplica cambios parciales sin confirmar la transacción."""
        for field, value in values.items():
            setattr(cost_center, field, value)
        self.db.flush()
        self.db.refresh(cost_center)
        return cost_center

    def is_referenced(self, cost_center_id: UUID) -> bool:
        """Indica si algún presupuesto, asiento o documento usa el centro.

        Las líneas de presupuesto se cubren a través de su cabecera: si existe
        un presupuesto del centro, el centro está referenciado.
        """
        for statement in (
            select(Budget.id).where(Budget.cost_center_id == cost_center_id),
            select(AccountingEntryLine.id).where(
                AccountingEntryLine.cost_center_id == cost_center_id
            ),
            select(PurchaseInvoice.id).where(PurchaseInvoice.cost_center_id == cost_center_id),
            select(Expense.id).where(Expense.cost_center_id == cost_center_id),
            select(PayrollPeriod.id).where(PayrollPeriod.cost_center_id == cost_center_id),
        ):
            if self.db.scalar(statement.limit(1)) is not None:
                return True
        return False

    def delete(self, cost_center: CostCenter) -> None:
        """Elimina físicamente el centro de costo sin confirmar."""
        self.db.delete(cost_center)
        self.db.flush()


__all__ = ["CostCenterRepository"]
