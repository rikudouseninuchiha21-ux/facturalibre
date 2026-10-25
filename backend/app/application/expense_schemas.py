"""Schemas Pydantic para el recurso Expense (gastos operativos)."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

Money = Annotated[Decimal, Field(max_digits=18, decimal_places=2, gt=0)]


class ExpenseCreate(BaseModel):
    """Datos para crear un gasto operativo."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    date: date
    concept: str = Field(min_length=1, max_length=200)
    amount: Money
    payment_method: str = Field(min_length=1, max_length=50)
    reference: str | None = Field(default=None, max_length=200)


class ExpenseRead(BaseModel):
    """Representación pública de un gasto operativo."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    date: date
    concept: str
    amount: Decimal
    payment_method: str
    reference: str | None
    bank_movement_id: UUID | None
    version: int
    created_at: datetime
    updated_at: datetime


__all__ = ["ExpenseCreate", "ExpenseRead"]
