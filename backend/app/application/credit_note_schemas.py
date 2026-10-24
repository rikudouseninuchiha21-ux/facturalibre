"""Schemas Pydantic y canonicalización para notas crédito."""

from __future__ import annotations

import hashlib
import json
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Annotated, Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.domain.models.credit_note import CreditNoteStatus

Money = Annotated[Decimal, Field(max_digits=18, decimal_places=2, ge=0)]
Quantity = Annotated[Decimal, Field(max_digits=18, decimal_places=4, gt=0)]
TaxRate = Annotated[Decimal, Field(max_digits=7, decimal_places=4, ge=0, le=100)]


class CreditNoteLineCreate(BaseModel):
    """Datos de una línea al crear una nota crédito."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    invoice_line_id: UUID | None = None
    description: str = Field(min_length=1, max_length=500)
    quantity: Quantity
    unit_price: Money
    tax_rate: TaxRate = Decimal("0")


class CreditNoteCreate(BaseModel):
    """Datos para crear una nota crédito en borrador."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    issue_date: date
    lines: list[CreditNoteLineCreate] = Field(min_length=1)


class CreditNoteLineRead(BaseModel):
    """Representación pública de una línea de nota crédito."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    invoice_line_id: UUID | None
    description: str
    quantity: Decimal
    unit_price: Decimal
    tax_rate: Decimal
    line_subtotal: Decimal
    line_tax: Decimal
    line_total: Decimal


class CreditNoteRead(BaseModel):
    """Representación pública de una nota crédito con sus líneas."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    number: str | None
    invoice_id: UUID
    issue_date: date
    status: CreditNoteStatus
    subtotal: Decimal
    tax_total: Decimal
    total: Decimal
    version: int
    created_at: datetime
    updated_at: datetime
    lines: list[CreditNoteLineRead]


def _canonicalize(value: Any) -> Any:
    """Normaliza tipos para que el hash no dependa del formato de entrada."""
    if isinstance(value, Decimal):
        return format(value.normalize(), "f")
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {str(key): _canonicalize(item) for key, item in value.items() if item is not None}
    if isinstance(value, (list, tuple)):
        return [_canonicalize(item) for item in value]
    return value


def canonical_body_hash(payload: CreditNoteCreate) -> str:
    """Calcula SHA-256 del body normalizado, con claves ordenadas."""
    canonical = _canonicalize(payload.model_dump(mode="python"))
    encoded = json.dumps(
        canonical,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
