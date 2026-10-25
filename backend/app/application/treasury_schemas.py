"""Schemas Pydantic del módulo de bancos y tesorería."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Literal, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.domain.models.bank import BankAccountType, BankTransactionType

Money = Annotated[Decimal, Field(max_digits=18, decimal_places=2, gt=0)]


class BankAccountCreate(BaseModel):
    """Datos para registrar una cuenta bancaria."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    name: str = Field(min_length=1, max_length=100)
    bank_name: str = Field(min_length=1, max_length=100)
    account_number: str = Field(min_length=1, max_length=50)
    account_type: BankAccountType = BankAccountType.CHECKING
    currency: Literal["COP"] = "COP"
    accounting_account_code: str = Field(default="111005", min_length=1, max_length=20)


class BankAccountUpdate(BaseModel):
    """Actualización parcial de una cuenta bancaria."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=100)
    is_active: bool | None = None
    version: int = Field(ge=1)

    @model_validator(mode="after")
    def validate_changes(self) -> Self:
        """Exige al menos un campo editable además de la versión."""
        if self.name is None and self.is_active is None:
            raise ValueError("Debe enviar al menos un campo para actualizar")
        return self


class BankAccountRead(BaseModel):
    """Cuenta bancaria con saldos derivados de sus movimientos."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    bank_name: str
    account_number: str
    account_type: BankAccountType
    currency: str
    accounting_account_code: str
    accounting_account_name: str
    is_active: bool
    balance: Decimal
    reconciled_balance: Decimal
    unreconciled_balance: Decimal
    unreconciled_transactions: int
    version: int
    created_at: datetime
    updated_at: datetime


class BankTransactionCreate(BaseModel):
    """Datos para registrar un movimiento de tesorería."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    transaction_type: BankTransactionType
    date: date
    amount: Money
    description: str = Field(min_length=1, max_length=200)
    reference: str | None = Field(default=None, max_length=100)
    counterpart_account_id: UUID | None = None
    counterpart_account_code: str | None = Field(default=None, max_length=20)

    @model_validator(mode="after")
    def validate_counterpart(self) -> Self:
        """Valida la contrapartida según el tipo de movimiento."""
        if self.transaction_type == BankTransactionType.TRANSFER:
            if self.counterpart_account_id is None:
                raise ValueError("Una transferencia requiere counterpart_account_id")
            if self.counterpart_account_code is not None:
                raise ValueError("Una transferencia no acepta counterpart_account_code")
            return self

        if self.counterpart_account_code is None:
            raise ValueError("Un depósito o retiro requiere counterpart_account_code")
        if self.counterpart_account_id is not None:
            raise ValueError("Un depósito o retiro no acepta counterpart_account_id")
        return self


class BankTransactionRead(BaseModel):
    """Movimiento bancario con los nombres de sus cuentas."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    bank_account_id: UUID
    bank_account_name: str
    transaction_type: BankTransactionType
    date: date
    amount: Decimal
    description: str
    reference: str | None
    counterpart_account_id: UUID | None
    counterpart_account_name: str | None
    counterpart_account_code: str | None
    is_reconciled: bool
    reconciled_at: datetime | None
    version: int
    created_at: datetime
    updated_at: datetime


class ReconcileRequest(BaseModel):
    """Versión esperada para marcar o desmarcar una conciliación."""

    model_config = ConfigDict(extra="forbid")

    version: int = Field(ge=1)


class TreasurySummary(BaseModel):
    """Totales agregados de tesorería."""

    total_balance: Decimal
    total_reconciled_balance: Decimal
    total_unreconciled_balance: Decimal
    total_accounts: int
    active_accounts: int
    unreconciled_transactions: int


__all__ = [
    "BankAccountCreate",
    "BankAccountRead",
    "BankAccountUpdate",
    "BankTransactionCreate",
    "BankTransactionRead",
    "ReconcileRequest",
    "TreasurySummary",
]
