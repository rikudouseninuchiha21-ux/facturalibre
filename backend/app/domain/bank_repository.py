"""Repositorio de cuentas bancarias y movimientos de tesorería.

Ningún método confirma la transacción. La capa de API agrupa el movimiento con
su asiento contable mediante ``operation_transaction``.
"""

from __future__ import annotations

import builtins
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any, cast
from uuid import UUID

from sqlalchemy import case, func, or_, select, update
from sqlalchemy.engine import CursorResult
from sqlalchemy.orm import Session, selectinload

from app.domain.exceptions import ResourceNotFoundError, VersionConflictError
from app.domain.models.bank import (
    BankAccount,
    BankTransaction,
    BankTransactionType,
)

ZERO = Decimal("0.00")


@dataclass(frozen=True)
class AccountBalanceSummary:
    """Saldos y estado de conciliación de una cuenta bancaria."""

    balance: Decimal
    reconciled_balance: Decimal
    unreconciled_count: int


class BankAccountRepository:
    """Acceso a cuentas bancarias."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, values: dict[str, Any]) -> BankAccount:
        account = BankAccount(**values)
        self.db.add(account)
        self.db.flush()
        self.db.refresh(account)
        return account

    def get_by_id(self, account_id: UUID) -> BankAccount | None:
        statement = select(BankAccount).where(
            BankAccount.id == account_id,
            BankAccount.deleted_at.is_(None),
        )
        return self.db.scalar(statement)

    def get_by_bank_details(
        self,
        *,
        bank_name: str,
        account_number: str,
    ) -> BankAccount | None:
        statement = select(BankAccount).where(
            BankAccount.bank_name == bank_name,
            BankAccount.account_number == account_number,
            BankAccount.deleted_at.is_(None),
        )
        return self.db.scalar(statement)

    def list(self, limit: int, offset: int) -> list[BankAccount]:
        statement = (
            select(BankAccount)
            .where(BankAccount.deleted_at.is_(None))
            .order_by(BankAccount.is_active.desc(), BankAccount.name, BankAccount.id)
            .limit(limit)
            .offset(offset)
        )
        return list(self.db.scalars(statement).all())

    def list_all(self) -> builtins.list[BankAccount]:
        """Lista todas las cuentas activas e inactivas, sin paginación.

        Se usa para calcular los totales de tesorería, donde el número de
        cuentas es pequeño por naturaleza.
        """
        statement = (
            select(BankAccount)
            .where(BankAccount.deleted_at.is_(None))
            .order_by(BankAccount.is_active.desc(), BankAccount.name, BankAccount.id)
        )
        return list(self.db.scalars(statement).all())

    def update(
        self,
        account_id: UUID,
        expected_version: int,
        values: dict[str, Any],
    ) -> BankAccount:
        """Actualiza con bloqueo optimista y sin confirmar la transacción."""
        statement = (
            update(BankAccount)
            .where(
                BankAccount.id == account_id,
                BankAccount.version == expected_version,
                BankAccount.deleted_at.is_(None),
            )
            .values(
                **values,
                version=BankAccount.version + 1,
                updated_at=func.now(),
            )
        )
        result = cast(CursorResult[Any], self.db.execute(statement))

        if result.rowcount == 0:
            self._raise_update_error(account_id)

        updated = self.get_by_id(account_id)
        if updated is None:
            raise ResourceNotFoundError("Cuenta bancaria no encontrada")
        return updated

    def get_balance_summaries(self) -> dict[UUID, AccountBalanceSummary]:
        """Calcula saldos de todas las cuentas en dos agregaciones."""
        outgoing = self._outgoing_aggregate()
        incoming = self._incoming_transfer_aggregate()

        summaries: dict[UUID, AccountBalanceSummary] = {}

        for row in self.db.execute(outgoing):
            summaries[row.account_id] = AccountBalanceSummary(
                balance=Decimal(str(row.balance)),
                reconciled_balance=Decimal(str(row.reconciled_balance)),
                unreconciled_count=int(row.unreconciled_count),
            )

        for row in self.db.execute(incoming):
            existing = summaries.get(row.account_id)
            if existing is None:
                summaries[row.account_id] = AccountBalanceSummary(
                    balance=Decimal(str(row.balance)),
                    reconciled_balance=Decimal(str(row.reconciled_balance)),
                    unreconciled_count=int(row.unreconciled_count),
                )
                continue

            summaries[row.account_id] = AccountBalanceSummary(
                balance=existing.balance + Decimal(str(row.balance)),
                reconciled_balance=(
                    existing.reconciled_balance + Decimal(str(row.reconciled_balance))
                ),
                unreconciled_count=(existing.unreconciled_count + int(row.unreconciled_count)),
            )

        return summaries

    def get_balance_summary(self, account_id: UUID) -> AccountBalanceSummary:
        summaries = self.get_balance_summaries()
        return summaries.get(
            account_id,
            AccountBalanceSummary(
                balance=ZERO,
                reconciled_balance=ZERO,
                unreconciled_count=0,
            ),
        )

    def _outgoing_aggregate(self) -> Any:
        signed_amount = case(
            (
                BankTransaction.transaction_type == BankTransactionType.DEPOSIT,
                BankTransaction.amount,
            ),
            (
                BankTransaction.transaction_type == BankTransactionType.WITHDRAWAL,
                -BankTransaction.amount,
            ),
            (
                BankTransaction.transaction_type == BankTransactionType.TRANSFER,
                -BankTransaction.amount,
            ),
            else_=Decimal("0"),
        )
        return (
            select(
                BankTransaction.bank_account_id.label("account_id"),
                func.coalesce(func.sum(signed_amount), 0).label("balance"),
                func.coalesce(
                    func.sum(
                        case(
                            (BankTransaction.is_reconciled.is_(True), signed_amount),
                            else_=Decimal("0"),
                        )
                    ),
                    0,
                ).label("reconciled_balance"),
                func.coalesce(
                    func.sum(
                        case(
                            (BankTransaction.is_reconciled.is_(False), 1),
                            else_=0,
                        )
                    ),
                    0,
                ).label("unreconciled_count"),
            )
            .where(BankTransaction.deleted_at.is_(None))
            .group_by(BankTransaction.bank_account_id)
        )

    def _incoming_transfer_aggregate(self) -> Any:
        return (
            select(
                BankTransaction.counterpart_account_id.label("account_id"),
                func.coalesce(func.sum(BankTransaction.amount), 0).label("balance"),
                func.coalesce(
                    func.sum(
                        case(
                            (BankTransaction.is_reconciled.is_(True), BankTransaction.amount),
                            else_=Decimal("0"),
                        )
                    ),
                    0,
                ).label("reconciled_balance"),
                func.coalesce(
                    func.sum(
                        case(
                            (BankTransaction.is_reconciled.is_(False), 1),
                            else_=0,
                        )
                    ),
                    0,
                ).label("unreconciled_count"),
            )
            .where(
                BankTransaction.transaction_type == BankTransactionType.TRANSFER,
                BankTransaction.counterpart_account_id.is_not(None),
                BankTransaction.deleted_at.is_(None),
            )
            .group_by(BankTransaction.counterpart_account_id)
        )

    def _raise_update_error(self, account_id: UUID) -> None:
        exists = self.db.scalar(
            select(BankAccount.id).where(
                BankAccount.id == account_id,
                BankAccount.deleted_at.is_(None),
            )
        )
        if exists is None:
            raise ResourceNotFoundError("Cuenta bancaria no encontrada")
        raise VersionConflictError("La versión de la cuenta bancaria no coincide")


class BankTransactionRepository:
    """Acceso a movimientos bancarios."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, values: dict[str, Any]) -> BankTransaction:
        transaction = BankTransaction(**values)
        self.db.add(transaction)
        self.db.flush()
        self.db.refresh(transaction)
        return transaction

    def get_by_id(self, transaction_id: UUID) -> BankTransaction | None:
        statement = (
            select(BankTransaction)
            .where(
                BankTransaction.id == transaction_id,
                BankTransaction.deleted_at.is_(None),
            )
            .options(
                selectinload(BankTransaction.bank_account),
                selectinload(BankTransaction.counterpart_account),
            )
        )
        return self.db.scalar(statement)

    def list_by_account(
        self,
        account_id: UUID,
        *,
        limit: int,
        offset: int,
    ) -> list[BankTransaction]:
        """Lista movimientos propios y transferencias recibidas por la cuenta."""
        statement = (
            select(BankTransaction)
            .where(
                or_(
                    BankTransaction.bank_account_id == account_id,
                    BankTransaction.counterpart_account_id == account_id,
                ),
                BankTransaction.deleted_at.is_(None),
            )
            .options(
                selectinload(BankTransaction.bank_account),
                selectinload(BankTransaction.counterpart_account),
            )
            .order_by(
                BankTransaction.date.desc(),
                BankTransaction.created_at.desc(),
                BankTransaction.id,
            )
            .limit(limit)
            .offset(offset)
        )
        return list(self.db.scalars(statement).all())

    def set_reconciled(
        self,
        transaction_id: UUID,
        expected_version: int,
        *,
        reconciled: bool,
    ) -> BankTransaction:
        """Marca o desmarca la conciliación con bloqueo optimista."""
        reconciled_at: datetime | None = datetime.now(UTC) if reconciled else None
        statement = (
            update(BankTransaction)
            .where(
                BankTransaction.id == transaction_id,
                BankTransaction.version == expected_version,
                BankTransaction.deleted_at.is_(None),
            )
            .values(
                is_reconciled=reconciled,
                reconciled_at=reconciled_at,
                version=BankTransaction.version + 1,
                updated_at=func.now(),
            )
        )
        result = cast(CursorResult[Any], self.db.execute(statement))

        if result.rowcount == 0:
            self._raise_update_error(transaction_id)

        updated = self.get_by_id(transaction_id)
        if updated is None:
            raise ResourceNotFoundError("Movimiento bancario no encontrado")
        return updated

    def _raise_update_error(self, transaction_id: UUID) -> None:
        exists = self.db.scalar(
            select(BankTransaction.id).where(
                BankTransaction.id == transaction_id,
                BankTransaction.deleted_at.is_(None),
            )
        )
        if exists is None:
            raise ResourceNotFoundError("Movimiento bancario no encontrado")
        raise VersionConflictError("La versión del movimiento bancario no coincide")


__all__ = [
    "AccountBalanceSummary",
    "BankAccountRepository",
    "BankTransactionRepository",
]
