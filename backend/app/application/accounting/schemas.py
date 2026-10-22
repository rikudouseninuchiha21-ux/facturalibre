"""Schemas de consulta del módulo de contabilidad."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, computed_field

from app.domain.models.accounting import (
    AccountingEntryStatus,
    AccountingSourceType,
    AccountNature,
    AccountType,
)


class AccountingAccountRead(BaseModel):
    """Cuenta del catálogo PUC."""

    model_config = ConfigDict(from_attributes=True)

    code: str
    name: str
    account_type: AccountType
    nature: AccountNature
    parent_code: str | None


class AccountingEntryLineRead(BaseModel):
    """Movimiento de un asiento contable."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    account_code: str
    account_name: str
    debit: Decimal
    credit: Decimal


class AccountingEntryRead(BaseModel):
    """Asiento contable con sus movimientos y totales de control."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    entry_date: date
    description: str
    source_type: AccountingSourceType
    source_id: UUID
    status: AccountingEntryStatus
    created_at: datetime
    lines: list[AccountingEntryLineRead]

    @computed_field  # type: ignore[prop-decorator]
    @property
    def total_debit(self) -> Decimal:
        """Suma de débitos del asiento."""
        return sum((line.debit for line in self.lines), Decimal("0.00"))

    @computed_field  # type: ignore[prop-decorator]
    @property
    def total_credit(self) -> Decimal:
        """Suma de créditos del asiento."""
        return sum((line.credit for line in self.lines), Decimal("0.00"))
