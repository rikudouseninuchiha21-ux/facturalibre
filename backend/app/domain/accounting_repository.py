"""Acceso a datos del catálogo PUC y de los asientos contables."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import date
from decimal import Decimal
from typing import Any, cast
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.domain.models.accounting import (
    AccountingAccount,
    AccountingEntry,
    AccountingEntryLine,
    AccountingEntryStatus,
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

    def get_account_balances(
        self,
        *,
        as_of_date: date | None = None,
    ) -> list[dict]:
        """Calcula el saldo de cada cuenta contable hasta una fecha de corte.

        El saldo se calcula como:
        - Cuentas de naturaleza Débito (ACTIVO, GASTO, COSTO): total_debit - total_credit
        - Cuentas de naturaleza Crédito (PASIVO, PATRIMONIO, INGRESO): total_credit - total_debit

        Se consideran solo asientos con estado POSTED y, si se indica,
        solo aquellas entradas con fecha <= as_of_date.
        """
        # Subquery: sumas por cuenta de los asientos posted hasta la fecha de corte
        line_subquery = (
            select(
                AccountingEntryLine.account_code,
                func.coalesce(func.sum(AccountingEntryLine.debit), 0).label("total_debit"),
                func.coalesce(func.sum(AccountingEntryLine.credit), 0).label("total_credit"),
            )
            .join(
                AccountingEntry,
                AccountingEntry.id == AccountingEntryLine.entry_id,
            )
            .where(AccountingEntry.status == AccountingEntryStatus.POSTED)
        )
        if as_of_date is not None:
            line_subquery = line_subquery.where(AccountingEntry.entry_date <= as_of_date)
        line_subquery = cast(
            Any,
            line_subquery.group_by(AccountingEntryLine.account_code).subquery(),
        )

        statement = (
            select(
                AccountingAccount.code,
                AccountingAccount.name,
                AccountingAccount.account_type,
                AccountingAccount.nature,
                func.coalesce(line_subquery.c.total_debit, 0).label("total_debit"),
                func.coalesce(line_subquery.c.total_credit, 0).label("total_credit"),
            )
            .outerjoin(
                line_subquery,
                line_subquery.c.account_code == AccountingAccount.code,
            )
            .order_by(AccountingAccount.code)
        )

        rows = self.db.execute(statement).all()
        results: list[dict] = []
        for row in rows:
            total_debit = Decimal(str(row.total_debit))
            total_credit = Decimal(str(row.total_credit))
            nature = row.nature
            if nature == "DEBITO":
                balance = total_debit - total_credit
            else:
                balance = total_credit - total_debit
            results.append(
                {
                    "code": row.code,
                    "name": row.name,
                    "account_type": row.account_type,
                    "nature": row.nature,
                    "balance": balance,
                }
            )
        return results
