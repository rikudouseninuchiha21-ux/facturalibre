"""Consultas y actualizaciones para conciliación bancaria.

La conciliación vincula un movimiento bancario con su pago de cliente o gasto
del sistema. El repositorio no confirma la transacción; la API coordina la
operación con ``operation_transaction``.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.calculations import round_money
from app.domain.models.bank import BankTransaction
from app.domain.models.contact import Contact
from app.domain.models.expense import Expense
from app.domain.models.invoice import Invoice
from app.domain.models.payment import Payment

ReconciliationKind = Literal["payment", "expense"]


@dataclass(frozen=True)
class ReconciliationTransactionRow:
    """Pago o gasto candidato para conciliar."""

    id: UUID
    kind: ReconciliationKind
    date: date
    amount: Decimal
    description: str
    reference: str | None
    party_name: str
    invoice_number: str | None = None


class ReconciliationRepository:
    """Acceso a movimientos y transacciones del sistema para conciliación."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def list_unreconciled_movements(self, account_id: UUID) -> list[BankTransaction]:
        """Lista movimientos no conciliados que pertenecen a la cuenta."""
        statement = (
            select(BankTransaction)
            .where(
                BankTransaction.bank_account_id == account_id,
                BankTransaction.deleted_at.is_(None),
                BankTransaction.is_reconciled.is_(False),
            )
            .order_by(
                BankTransaction.date.desc(),
                BankTransaction.created_at.desc(),
                BankTransaction.id,
            )
        )
        return list(self.db.scalars(statement).all())

    def list_unlinked_payments(self) -> list[ReconciliationTransactionRow]:
        """Lista pagos de clientes aún no vinculados a un movimiento bancario."""
        statement = (
            select(
                Payment.id,
                Payment.payment_date,
                Payment.amount,
                Payment.reference,
                Payment.method,
                Invoice.number,
                Contact.name,
            )
            .join(Invoice, Invoice.id == Payment.invoice_id)
            .join(Contact, Contact.id == Invoice.contact_id)
            .where(
                Payment.bank_movement_id.is_(None),
                Invoice.deleted_at.is_(None),
            )
            .order_by(
                Payment.payment_date.desc(),
                Payment.id,
            )
        )
        rows = self.db.execute(statement).all()
        return [
            ReconciliationTransactionRow(
                id=payment_id,
                kind="payment",
                date=payment_date,
                amount=round_money(amount),
                description=(
                    f"Pago factura {invoice_number}"
                    if invoice_number is not None
                    else "Pago de cliente"
                ),
                reference=reference or method,
                party_name=contact_name,
                invoice_number=invoice_number,
            )
            for (
                payment_id,
                payment_date,
                amount,
                reference,
                method,
                invoice_number,
                contact_name,
            ) in rows
        ]

    def list_unlinked_expenses(self) -> list[ReconciliationTransactionRow]:
        """Lista gastos aún no vinculados a un movimiento bancario."""
        statement = (
            select(
                Expense.id,
                Expense.date,
                Expense.amount,
                Expense.concept,
                Expense.reference,
                Expense.payment_method,
            )
            .where(
                Expense.bank_movement_id.is_(None),
                Expense.deleted_at.is_(None),
            )
            .order_by(
                Expense.date.desc(),
                Expense.id,
            )
        )
        rows = self.db.execute(statement).all()
        return [
            ReconciliationTransactionRow(
                id=expense_id,
                kind="expense",
                date=expense_date,
                amount=round_money(amount),
                description=concept,
                reference=reference or payment_method,
                party_name="Gasto operativo",
            )
            for (
                expense_id,
                expense_date,
                amount,
                concept,
                reference,
                payment_method,
            ) in rows
        ]

    def get_movement_for_reconciliation(
        self,
        account_id: UUID,
        movement_id: UUID,
    ) -> BankTransaction | None:
        """Bloquea un movimiento de la cuenta para conciliarlo."""
        statement = (
            select(BankTransaction)
            .where(
                BankTransaction.id == movement_id,
                BankTransaction.bank_account_id == account_id,
                BankTransaction.deleted_at.is_(None),
            )
            .with_for_update()
        )
        return self.db.scalar(statement)

    def get_payment_for_reconciliation(self, payment_id: UUID) -> Payment | None:
        """Bloquea un pago para evitar conciliaciones concurrentes."""
        statement = select(Payment).where(Payment.id == payment_id).with_for_update()
        return self.db.scalar(statement)

    def get_expense_for_reconciliation(self, expense_id: UUID) -> Expense | None:
        """Bloquea un gasto no eliminado para evitar conciliaciones concurrentes."""
        statement = (
            select(Expense)
            .where(
                Expense.id == expense_id,
                Expense.deleted_at.is_(None),
            )
            .with_for_update()
        )
        return self.db.scalar(statement)

    def movement_is_linked(self, movement_id: UUID) -> bool:
        """Indica si el movimiento ya está vinculado a un pago o gasto."""
        payment_id = self.db.scalar(
            select(Payment.id)
            .where(Payment.bank_movement_id == movement_id)
            .limit(1)
        )
        if payment_id is not None:
            return True
        expense_id = self.db.scalar(
            select(Expense.id)
            .where(Expense.bank_movement_id == movement_id)
            .limit(1)
        )
        return expense_id is not None

    def link_payment(self, payment: Payment, movement_id: UUID) -> None:
        """Vincula un pago con un movimiento bancario."""
        payment.bank_movement_id = movement_id
        self.db.flush()

    def link_expense(self, expense: Expense, movement_id: UUID) -> None:
        """Vincula un gasto con un movimiento bancario."""
        expense.bank_movement_id = movement_id
        expense.version += 1
        self.db.flush()

    def unlink_movement(self, movement_id: UUID) -> None:
        """Desvincula pagos y gastos de un movimiento al desconciliarlo.

        Se recorre el identity map para que la sesión de la petición vea el
        cambio inmediatamente, sin dejar objetos obsoletos.
        """
        payments = self.db.scalars(
            select(Payment).where(Payment.bank_movement_id == movement_id)
        ).all()
        for payment in payments:
            payment.bank_movement_id = None

        expenses = self.db.scalars(
            select(Expense).where(Expense.bank_movement_id == movement_id)
        ).all()
        for expense in expenses:
            expense.bank_movement_id = None
            expense.version += 1

        self.db.flush()

    def mark_movement_reconciled(self, movement: BankTransaction) -> None:
        """Marca el movimiento como conciliado con el extracto."""
        movement.is_reconciled = True
        movement.reconciled_at = self._now()
        movement.version += 1
        self.db.flush()

    @staticmethod
    def _now() -> datetime:
        """Devuelve el timestamp actual con zona horaria.

        Se aísla en un método para mantener el repositorio fácil de probar y
        evitar que la lógica de negocio dependa de una fecha fija.
        """
        return datetime.now(UTC)


__all__ = [
    "ReconciliationKind",
    "ReconciliationRepository",
    "ReconciliationTransactionRow",
]
