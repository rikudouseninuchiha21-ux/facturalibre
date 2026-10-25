"""Repositorio de gastos operativos con SQLAlchemy 2.

El repositorio nunca confirma transacciones. La capa de API agrupa el gasto y
su asiento contable con ``operation_transaction`` para que se confirmen o
reviertan juntos.
"""

from __future__ import annotations

from typing import Any, cast
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.engine import CursorResult
from sqlalchemy.orm import Session

from app.domain.exceptions import ResourceNotFoundError
from app.domain.models.expense import Expense


class ExpenseRepository:
    """Acceso a datos de gastos operativos; excluye soft-deleted por defecto."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, values: dict[str, Any]) -> Expense:
        """Crea un gasto y lo persiste sin confirmar la transacción."""
        expense = Expense(**values)
        self.db.add(expense)
        self.db.flush()
        self.db.refresh(expense)
        return expense

    def get_by_id(self, expense_id: UUID) -> Expense | None:
        statement = select(Expense).where(
            Expense.id == expense_id,
            Expense.deleted_at.is_(None),
        )
        return self.db.scalar(statement)

    def list(self, limit: int, offset: int) -> list[Expense]:
        statement = (
            select(Expense)
            .where(Expense.deleted_at.is_(None))
            .order_by(Expense.date.desc(), Expense.created_at.desc(), Expense.id)
            .limit(limit)
            .offset(offset)
        )
        return list(self.db.scalars(statement).all())

    def soft_delete(self, expense_id: UUID) -> None:
        """Marca el gasto como eliminado sin confirmar la transacción."""
        statement = (
            update(Expense)
            .where(Expense.id == expense_id, Expense.deleted_at.is_(None))
            .values(
                deleted_at=func.now(),
                updated_at=func.now(),
                version=Expense.version + 1,
            )
        )
        result = cast(CursorResult[Any], self.db.execute(statement))

        if result.rowcount == 0:
            raise ResourceNotFoundError("Gasto no encontrado")


__all__ = ["ExpenseRepository"]
