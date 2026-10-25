"""Acceso a datos del catálogo PUC y de los asientos contables."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Any, cast
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.domain.models.accounting import (
    AccountingAccount,
    AccountingEntry,
    AccountingEntryLine,
    AccountingEntryStatus,
    AccountingSourceType,
    FiscalPeriod,
    FiscalPeriodStatus,
)


@dataclass(frozen=True)
class LedgerMovementRow:
    """Movimiento de una cuenta con los datos del Libro Mayor."""

    id: UUID
    entry_id: UUID
    entry_date: date
    description: str
    source_type: AccountingSourceType
    debit: Decimal
    credit: Decimal


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

    def search_accounts(
        self,
        *,
        query: str | None,
        limit: int,
    ) -> list[AccountingAccount]:
        """Busca cuentas PUC por código o nombre para el selector del Libro Mayor."""
        statement = select(AccountingAccount).order_by(AccountingAccount.code).limit(limit)
        if query:
            term = f"%{query.strip()}%"
            statement = statement.where(
                or_(
                    AccountingAccount.code.ilike(term),
                    AccountingAccount.name.ilike(term),
                )
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

    def get_account_by_code(self, code: str) -> AccountingAccount | None:
        """Obtiene una cuenta PUC por su código."""
        return self.db.get(AccountingAccount, code)

    def is_period_closed(self, *, year: int, month: int) -> bool:
        """Indica si el periodo mensual está cerrado.

        La ausencia de fila significa que el periodo está abierto: solo el
        cierre explícito crea el registro.
        """
        statement = select(FiscalPeriod.id).where(
            FiscalPeriod.year == year,
            FiscalPeriod.month == month,
            FiscalPeriod.status == FiscalPeriodStatus.CLOSED,
        )
        return self.db.scalar(statement) is not None

    def get_account_totals_before(
        self,
        *,
        account_code: str,
        before_date: date,
    ) -> tuple[Decimal, Decimal]:
        """Suma débitos y créditos POSTED de una cuenta antes de una fecha."""
        statement = (
            select(
                func.coalesce(func.sum(AccountingEntryLine.debit), 0),
                func.coalesce(func.sum(AccountingEntryLine.credit), 0),
            )
            .join(AccountingEntry, AccountingEntry.id == AccountingEntryLine.entry_id)
            .where(
                AccountingEntryLine.account_code == account_code,
                AccountingEntry.status == AccountingEntryStatus.POSTED,
                AccountingEntry.entry_date < before_date,
            )
        )
        total_debit, total_credit = self.db.execute(statement).one()
        return Decimal(str(total_debit)), Decimal(str(total_credit))

    def list_account_movements(
        self,
        *,
        account_code: str,
        start_date: date | None,
        end_date: date | None,
    ) -> list[LedgerMovementRow]:
        """Lista los movimientos POSTED de una cuenta ordenados por fecha."""
        statement = (
            select(
                AccountingEntryLine.id,
                AccountingEntry.id,
                AccountingEntry.entry_date,
                AccountingEntry.description,
                AccountingEntry.source_type,
                AccountingEntryLine.debit,
                AccountingEntryLine.credit,
            )
            .join(AccountingEntry, AccountingEntry.id == AccountingEntryLine.entry_id)
            .where(
                AccountingEntryLine.account_code == account_code,
                AccountingEntry.status == AccountingEntryStatus.POSTED,
            )
            .order_by(
                AccountingEntry.entry_date,
                AccountingEntry.created_at,
                AccountingEntry.id,
                AccountingEntryLine.id,
            )
        )
        if start_date is not None:
            statement = statement.where(AccountingEntry.entry_date >= start_date)
        if end_date is not None:
            statement = statement.where(AccountingEntry.entry_date <= end_date)

        rows = self.db.execute(statement).all()
        return [
            LedgerMovementRow(
                id=row[0],
                entry_id=row[1],
                entry_date=row[2],
                description=row[3],
                source_type=row[4],
                debit=Decimal(str(row[5])),
                credit=Decimal(str(row[6])),
            )
            for row in rows
        ]

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
                    "total_debit": total_debit,
                    "total_credit": total_credit,
                    "balance": balance,
                }
            )
        return results


class FiscalPeriodRepository:
    """Acceso a los periodos contables y sus validaciones de cierre."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_period(self, *, year: int, month: int) -> FiscalPeriod | None:
        """Obtiene el periodo mensual si ya fue creado."""
        statement = select(FiscalPeriod).where(
            FiscalPeriod.year == year,
            FiscalPeriod.month == month,
        )
        return self.db.scalar(statement)

    def add_period(self, period: FiscalPeriod) -> FiscalPeriod:
        """Persiste un periodo sin confirmar la transacción."""
        self.db.add(period)
        self.db.flush()
        return period

    def list_unbalanced_entry_ids(self, *, year: int, month: int) -> list[UUID]:
        """Detecta asientos del mes cuyos débitos y créditos no coinciden.

        Se revisan todos los estados porque el cierre debe rechazar cualquier
        comprobante inconsistente, incluso si quedó en borrador. La consulta
        usa un outer join para incluir asientos sin líneas.
        """
        start = date(year, month, 1)
        end = date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)
        total_debit = func.coalesce(func.sum(AccountingEntryLine.debit), 0)
        total_credit = func.coalesce(func.sum(AccountingEntryLine.credit), 0)
        statement = (
            select(AccountingEntry.id)
            .outerjoin(
                AccountingEntryLine,
                AccountingEntryLine.entry_id == AccountingEntry.id,
            )
            .where(
                AccountingEntry.entry_date >= start,
                AccountingEntry.entry_date < end,
            )
            .group_by(AccountingEntry.id)
            .having(total_debit != total_credit)
        )
        return list(self.db.scalars(statement).all())
