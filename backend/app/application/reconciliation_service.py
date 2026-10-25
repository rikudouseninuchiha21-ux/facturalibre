"""Casos de uso de conciliación bancaria.

La conciliación es direccional: un depósito se cruza con un pago de cliente y
un retiro con un gasto. El servicio valida monto y una ventana de fechas antes
de vincular. No confirma la transacción; la API usa ``operation_transaction``.
"""

from __future__ import annotations

from datetime import date
from uuid import UUID

from sqlalchemy.orm import Session

from app.application.reconciliation_schemas import (
    ReconciliationBankMovementRead,
    ReconciliationCandidatesResponse,
    ReconciliationRequest,
    ReconciliationResult,
    ReconciliationTransactionRead,
)
from app.domain.bank_repository import BankAccountRepository
from app.domain.calculations import round_money
from app.domain.exceptions import (
    ResourceNotFoundError,
    TreasuryError,
    TreasuryValidationError,
)
from app.domain.models.bank import BankTransaction, BankTransactionType
from app.domain.models.expense import Expense
from app.domain.models.payment import Payment
from app.domain.reconciliation_repository import (
    ReconciliationRepository,
    ReconciliationTransactionRow,
)

MATCH_WINDOW_DAYS = 3


def _date_distance(left: date, right: date) -> int:
    """Distancia absoluta en días entre dos fechas."""
    return abs((left - right).days)


class ReconciliationService:
    """Calcula candidatos y ejecuta la vinculación de una conciliación."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.accounts = BankAccountRepository(db)
        self.reconciliation = ReconciliationRepository(db)

    def candidates(self, account_id: UUID) -> ReconciliationCandidatesResponse:
        """Devuelve movimientos pendientes con sus pagos/gastos compatibles."""
        account = self.accounts.get_by_id(account_id)
        if account is None:
            raise ResourceNotFoundError("Cuenta bancaria no encontrada")

        movements = self.reconciliation.list_unreconciled_movements(account_id)
        payments = self.reconciliation.list_unlinked_payments()
        expenses = self.reconciliation.list_unlinked_expenses()

        result: list[ReconciliationBankMovementRead] = []
        for movement in movements:
            if movement.transaction_type == BankTransactionType.DEPOSIT:
                candidates = [row for row in payments if self._matches(movement, row)]
            elif movement.transaction_type == BankTransactionType.WITHDRAWAL:
                candidates = [row for row in expenses if self._matches(movement, row)]
            else:
                # Una transferencia es un movimiento interno: no tiene
                # contrapartida en pagos ni gastos.
                candidates = []

            candidates.sort(
                key=lambda row: (
                    _date_distance(movement.date, row.date),
                    row.date,
                    str(row.id),
                )
            )
            result.append(
                ReconciliationBankMovementRead(
                    id=movement.id,
                    date=movement.date,
                    amount=round_money(movement.amount),
                    transaction_type=movement.transaction_type,
                    description=movement.description,
                    reference=movement.reference,
                    version=movement.version,
                    candidates=[self._candidate_read(row) for row in candidates],
                )
            )

        return ReconciliationCandidatesResponse(
            bank_account_id=account_id,
            bank_movements=result,
        )

    def reconcile(
        self,
        account_id: UUID,
        payload: ReconciliationRequest,
    ) -> ReconciliationResult:
        """Vincula un movimiento con un pago o gasto y lo marca conciliado."""
        account = self.accounts.get_by_id(account_id)
        if account is None:
            raise ResourceNotFoundError("Cuenta bancaria no encontrada")

        movement = self.reconciliation.get_movement_for_reconciliation(
            account_id,
            payload.bank_movement_id,
        )
        if movement is None:
            raise ResourceNotFoundError("Movimiento bancario no encontrado")
        if movement.is_reconciled:
            raise TreasuryError("El movimiento bancario ya está conciliado")
        if self.reconciliation.movement_is_linked(movement.id):
            raise TreasuryError("El movimiento bancario ya está vinculado a una transacción")

        if movement.transaction_type == BankTransactionType.DEPOSIT:
            transaction = self._reconcile_payment(movement, payload.transaction_id)
        elif movement.transaction_type == BankTransactionType.WITHDRAWAL:
            transaction = self._reconcile_expense(movement, payload.transaction_id)
        else:
            raise TreasuryValidationError(
                "Las transferencias internas no se concilian con pagos o gastos"
            )

        self.reconciliation.mark_movement_reconciled(movement)
        reconciled_at = movement.reconciled_at
        if reconciled_at is None:
            raise TreasuryError("No se pudo registrar la fecha de conciliación")

        return ReconciliationResult(
            bank_account_id=account_id,
            bank_movement_id=movement.id,
            bank_movement_date=movement.date,
            bank_movement_amount=round_money(movement.amount),
            transaction=transaction,
            is_reconciled=movement.is_reconciled,
            reconciled_at=reconciled_at,
        )

    def _reconcile_payment(
        self,
        movement: BankTransaction,
        transaction_id: UUID,
    ) -> ReconciliationTransactionRead:
        payment = self.reconciliation.get_payment_for_reconciliation(transaction_id)
        if payment is None:
            raise ResourceNotFoundError("No se encontró un pago de cliente con ese identificador")
        if payment.invoice.deleted_at is not None:
            raise ResourceNotFoundError("No se encontró un pago de cliente con ese identificador")
        if payment.bank_movement_id is not None:
            raise TreasuryError("El pago de cliente ya está conciliado")
        row = self._payment_row(payment)
        self._validate_match(movement, row)
        self.reconciliation.link_payment(payment, movement.id)
        return self._candidate_read(row)

    def _reconcile_expense(
        self,
        movement: BankTransaction,
        transaction_id: UUID,
    ) -> ReconciliationTransactionRead:
        expense = self.reconciliation.get_expense_for_reconciliation(transaction_id)
        if expense is None:
            raise ResourceNotFoundError("No se encontró un gasto con ese identificador")
        if expense.bank_movement_id is not None:
            raise TreasuryError("El gasto ya está conciliado")
        row = self._expense_row(expense)
        self._validate_match(movement, row)
        self.reconciliation.link_expense(expense, movement.id)
        return self._candidate_read(row)

    def _matches(
        self,
        movement: BankTransaction,
        transaction: ReconciliationTransactionRow,
    ) -> bool:
        """Aplica monto exacto y ventana de fechas a un candidato."""
        return (
            round_money(movement.amount) == round_money(transaction.amount)
            and _date_distance(movement.date, transaction.date) <= MATCH_WINDOW_DAYS
        )

    def _validate_match(
        self,
        movement: BankTransaction,
        transaction: ReconciliationTransactionRow,
    ) -> None:
        """Rechaza vínculos que no cumplen las reglas de conciliación."""
        if round_money(movement.amount) != round_money(transaction.amount):
            raise TreasuryValidationError(
                "El monto del movimiento bancario no coincide con la transacción"
            )
        if _date_distance(movement.date, transaction.date) > MATCH_WINDOW_DAYS:
            raise TreasuryValidationError(
                "La fecha del movimiento bancario está fuera de la ventana de 3 días"
            )

    @staticmethod
    def _payment_row(payment: Payment) -> ReconciliationTransactionRow:
        invoice = payment.invoice
        return ReconciliationTransactionRow(
            id=payment.id,
            kind="payment",
            date=payment.payment_date,
            amount=round_money(payment.amount),
            description=(
                f"Pago factura {invoice.number}"
                if invoice.number is not None
                else "Pago de cliente"
            ),
            reference=payment.reference or payment.method,
            party_name=invoice.contact.name,
            invoice_number=invoice.number,
        )

    @staticmethod
    def _expense_row(expense: Expense) -> ReconciliationTransactionRow:
        return ReconciliationTransactionRow(
            id=expense.id,
            kind="expense",
            date=expense.date,
            amount=round_money(expense.amount),
            description=expense.concept,
            reference=expense.reference or expense.payment_method,
            party_name="Gasto operativo",
        )

    @staticmethod
    def _candidate_read(
        row: ReconciliationTransactionRow,
    ) -> ReconciliationTransactionRead:
        return ReconciliationTransactionRead(
            id=row.id,
            kind=row.kind,
            date=row.date,
            amount=row.amount,
            description=row.description,
            reference=row.reference,
            party_name=row.party_name,
            invoice_number=row.invoice_number,
        )


__all__ = ["MATCH_WINDOW_DAYS", "ReconciliationService"]
