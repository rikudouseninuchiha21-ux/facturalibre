"""Schemas Pydantic para la conciliación bancaria."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.domain.models.bank import BankTransactionType


class ReconciliationTransactionRead(BaseModel):
    """Pago o gasto candidato para vincular a un movimiento bancario."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    kind: Literal["payment", "expense"]
    date: date
    amount: Decimal
    description: str
    reference: str | None
    party_name: str
    invoice_number: str | None = None


class ReconciliationBankMovementRead(BaseModel):
    """Movimiento bancario pendiente con sus contrapartidas candidatas."""

    id: UUID
    date: date
    amount: Decimal
    transaction_type: BankTransactionType
    description: str
    reference: str | None
    version: int
    candidates: list[ReconciliationTransactionRead]


class ReconciliationCandidatesResponse(BaseModel):
    """Candidatos de conciliación para una cuenta bancaria."""

    bank_account_id: UUID
    bank_movements: list[ReconciliationBankMovementRead]


class ReconciliationRequest(BaseModel):
    """Identificadores que se van a vincular en una conciliación."""

    model_config = ConfigDict(extra="forbid")

    bank_movement_id: UUID
    transaction_id: UUID


class ReconciliationResult(BaseModel):
    """Resultado de una conciliación exitosa."""

    bank_account_id: UUID
    bank_movement_id: UUID
    bank_movement_date: date
    bank_movement_amount: Decimal
    transaction: ReconciliationTransactionRead
    is_reconciled: bool
    reconciled_at: datetime


__all__ = [
    "ReconciliationBankMovementRead",
    "ReconciliationCandidatesResponse",
    "ReconciliationRequest",
    "ReconciliationResult",
    "ReconciliationTransactionRead",
]
