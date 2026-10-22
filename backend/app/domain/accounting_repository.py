"""Acceso a datos del catálogo PUC y de los asientos contables."""

from __future__ import annotations

from collections.abc import Iterable
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.domain.models.accounting import (
    AccountingAccount,
    AccountingEntry,
    AccountingEntryLine,
    AccountingSourceType,
)


class AccountingRepository:
    """Consultas y persistencia del núcleo contable.

    No hace commit: el servicio y la capa de API controlan la transacción para
    que el asiento sea atómico con la operación de facturación que lo origina.
    """

    def __init__(self, db: Session) -> None:
        self.db = db

    def list_accounts(self, *, limit: int, offset: int) -> list[AccountingAccount]:
        """Lista el catálogo PUC ordenado por código."""
        statement = (
            select(AccountingAccount).order_by(AccountingAccount.code).limit(limit).offset(offset)
        )
        return list(self.db.scalars(statement).all())

    def get_accounts_by_codes(self, codes: Iterable[str]) -> dict[str, AccountingAccount]:
        """Carga en lote las cuentas usadas por un asiento."""
        unique_codes = set(codes)
        if not unique_codes:
            return {}
        statement = select(AccountingAccount).where(AccountingAccount.code.in_(unique_codes))
        return {account.code: account for account in self.db.scalars(statement).all()}

    def get_entry(
        self,
        entry_id: UUID,
    ) -> AccountingEntry | None:
        """Obtiene un asiento con sus movimientos y cuentas."""
        statement = (
            select(AccountingEntry)
            .where(AccountingEntry.id == entry_id)
            .options(selectinload(AccountingEntry.lines).selectinload(AccountingEntryLine.account))
        )
        return self.db.scalar(statement)

    def get_entry_by_source(
        self,
        source_type: AccountingSourceType,
        source_id: UUID,
    ) -> AccountingEntry | None:
        """Busca el asiento original de un evento de facturación."""
        statement = (
            select(AccountingEntry)
            .where(
                AccountingEntry.source_type == source_type,
                AccountingEntry.source_id == source_id,
            )
            .options(selectinload(AccountingEntry.lines).selectinload(AccountingEntryLine.account))
        )
        return self.db.scalar(statement)

    def list_entries(self, *, limit: int, offset: int) -> list[AccountingEntry]:
        """Lista asientos con sus movimientos, del más reciente al más antiguo."""
        statement = (
            select(AccountingEntry)
            .options(selectinload(AccountingEntry.lines).selectinload(AccountingEntryLine.account))
            .order_by(
                AccountingEntry.entry_date.desc(),
                AccountingEntry.created_at.desc(),
                AccountingEntry.id,
            )
            .limit(limit)
            .offset(offset)
        )
        return list(self.db.scalars(statement).all())

    def add_entry(self, entry: AccountingEntry) -> AccountingEntry:
        """Persiste el asiento y sus movimientos sin confirmar la transacción."""
        self.db.add(entry)
        self.db.flush()
        return entry
