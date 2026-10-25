"""Servicio de gastos operativos con generación automática de asiento contable.

El servicio no hace commit. La API controla la transacción vía
``operation_transaction`` para que el gasto y el asiento contable se
confirmen o reviertan juntos.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy.orm import Session

from app.application.accounting.service import AccountingService
from app.domain.exceptions import ResourceNotFoundError
from app.domain.expense_repository import ExpenseRepository
from app.domain.models.expense import Expense


class ExpenseService:
    """Lógica de negocio de gastos operativos."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.expenses = ExpenseRepository(db)
        self.accounting = AccountingService(db)

    def create_expense(
        self,
        *,
        date: date,
        concept: str,
        amount: Decimal,
        payment_method: str,
        reference: str | None = None,
    ) -> Expense:
        """Crea un gasto operativo y genera el asiento contable asociado.

        El asiento tiene:
        - Débito a Gastos diversos (5199) por el monto.
        - Crédito a Caja (110505) si el método es efectivo, o a Bancos (111005)
          en cualquier otro caso.
        """
        expense = self.expenses.create(
            {
                "date": date,
                "concept": concept,
                "amount": amount,
                "payment_method": payment_method,
                "reference": reference,
            }
        )

        self.accounting.record_expense(expense)

        self.db.flush()
        return expense

    def delete_expense(self, expense_id: UUID) -> None:
        """Elimina lógicamente un gasto y revierte su asiento contable.

        El gasto y el contra-asiento se confirman en la misma transacción de
        negocio. Si el gasto no existe se lanza ``ResourceNotFoundError``.
        """
        expense = self.expenses.get_by_id(expense_id)
        if expense is None:
            raise ResourceNotFoundError("Gasto no encontrado")

        self.accounting.record_expense_reversal(expense)
        self.expenses.soft_delete(expense_id)
        self.db.flush()


__all__ = ["ExpenseService"]
