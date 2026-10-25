"""Lógica de negocio de bancos y tesorería.

El servicio no confirma transacciones. La API agrupa cada movimiento con su
asiento contable mediante ``operation_transaction``.
"""

from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from sqlalchemy.orm import Session

from app.application.accounting.service import AccountingService
from app.application.treasury_schemas import (
    BankAccountCreate,
    BankAccountUpdate,
    BankTransactionCreate,
    TreasurySummary,
)
from app.domain.accounting_repository import AccountingRepository
from app.domain.bank_repository import (
    BankAccountRepository,
    BankTransactionRepository,
)
from app.domain.exceptions import (
    ResourceNotFoundError,
    TreasuryError,
    TreasuryValidationError,
)
from app.domain.models.accounting import AccountingAccount, AccountType
from app.domain.models.bank import (
    BankAccount,
    BankTransaction,
    BankTransactionType,
)

ZERO = Decimal("0.00")
BANK_PUC_PREFIX = "11"


class TreasuryService:
    """Casos de uso de cuentas bancarias, movimientos y conciliación."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.accounts = BankAccountRepository(db)
        self.transactions = BankTransactionRepository(db)
        self.accounting = AccountingService(db)
        self.puc = AccountingRepository(db)

    def create_account(self, payload: BankAccountCreate) -> BankAccount:
        """Registra una cuenta bancaria validando su cuenta PUC."""
        puc_account = self._require_puc_account(payload.accounting_account_code)
        if puc_account.account_type != AccountType.ACTIVO or not puc_account.code.startswith(
            BANK_PUC_PREFIX
        ):
            raise TreasuryValidationError(
                "La cuenta PUC debe ser una cuenta activa del grupo 11 (Disponible)"
            )

        existing = self.accounts.get_by_bank_details(
            bank_name=payload.bank_name,
            account_number=payload.account_number,
        )
        if existing is not None:
            raise TreasuryError("Ya existe una cuenta bancaria con ese banco y número de cuenta")

        return self.accounts.create(
            {
                "name": payload.name,
                "bank_name": payload.bank_name,
                "account_number": payload.account_number,
                "account_type": payload.account_type,
                "currency": payload.currency,
                "accounting_account_code": payload.accounting_account_code,
            }
        )

    def update_account(
        self,
        account_id: UUID,
        payload: BankAccountUpdate,
    ) -> BankAccount:
        """Actualiza nombre o estado de una cuenta con bloqueo optimista."""
        values: dict[str, object] = {}
        if payload.name is not None:
            values["name"] = payload.name
        if payload.is_active is not None:
            values["is_active"] = payload.is_active
        return self.accounts.update(account_id, payload.version, values)

    def create_transaction(
        self,
        account_id: UUID,
        payload: BankTransactionCreate,
    ) -> BankTransaction:
        """Registra un movimiento y su asiento contable en la misma transacción."""
        account = self.accounts.get_by_id(account_id)
        if account is None:
            raise ResourceNotFoundError("Cuenta bancaria no encontrada")
        if not account.is_active:
            raise TreasuryError("La cuenta bancaria está inactiva")

        counterpart_account: BankAccount | None = None

        if payload.transaction_type == BankTransactionType.TRANSFER:
            if payload.counterpart_account_id is None:
                raise TreasuryValidationError("La transferencia requiere una cuenta destino")
            counterpart_account = self.accounts.get_by_id(payload.counterpart_account_id)
            if counterpart_account is None:
                raise TreasuryValidationError("La cuenta destino no existe")
            if not counterpart_account.is_active:
                raise TreasuryError("La cuenta destino está inactiva")
            if counterpart_account.id == account.id:
                raise TreasuryValidationError("La cuenta origen y destino deben ser diferentes")
            if counterpart_account.accounting_account_code == account.accounting_account_code:
                raise TreasuryValidationError(
                    "Las cuentas deben tener códigos PUC distintos para transferir"
                )
        else:
            if payload.counterpart_account_code is None:
                raise TreasuryValidationError(
                    "El movimiento requiere una cuenta contable de contrapartida"
                )
            self._require_puc_account(payload.counterpart_account_code)
            if payload.counterpart_account_code == account.accounting_account_code:
                raise TreasuryValidationError(
                    "La contrapartida no puede ser la misma cuenta del banco"
                )

        transaction = self.transactions.create(
            {
                "bank_account_id": account.id,
                "counterpart_account_id": (
                    counterpart_account.id if counterpart_account is not None else None
                ),
                "transaction_type": payload.transaction_type,
                "date": payload.date,
                "amount": payload.amount,
                "description": payload.description,
                "reference": payload.reference,
                "counterpart_account_code": payload.counterpart_account_code,
            }
        )

        self.accounting.record_bank_transaction(
            transaction,
            account,
            counterpart_account,
        )
        self.db.flush()
        return transaction

    def set_reconciled(
        self,
        transaction_id: UUID,
        expected_version: int,
        *,
        reconciled: bool,
    ) -> BankTransaction:
        """Marca o desmarca un movimiento como conciliado."""
        return self.transactions.set_reconciled(
            transaction_id,
            expected_version,
            reconciled=reconciled,
        )

    def summary(self) -> TreasurySummary:
        """Calcula los totales de tesorería a partir de las cuentas."""
        accounts = self.accounts.list_all()
        balances = self.accounts.get_balance_summaries()

        total_balance = ZERO
        total_reconciled = ZERO
        unreconciled_transactions = 0
        active_accounts = 0

        for account in accounts:
            summary = balances.get(account.id)
            if summary is not None:
                total_balance += summary.balance
                total_reconciled += summary.reconciled_balance
                unreconciled_transactions += summary.unreconciled_count
            if account.is_active:
                active_accounts += 1

        return TreasurySummary(
            total_balance=total_balance,
            total_reconciled_balance=total_reconciled,
            total_unreconciled_balance=total_balance - total_reconciled,
            total_accounts=len(accounts),
            active_accounts=active_accounts,
            unreconciled_transactions=unreconciled_transactions,
        )

    def _require_puc_account(self, code: str) -> AccountingAccount:
        account = self.puc.get_accounts_by_codes([code]).get(code)
        if account is None:
            raise TreasuryValidationError(f"La cuenta PUC {code} no existe")
        return account


__all__ = ["TreasuryService"]
