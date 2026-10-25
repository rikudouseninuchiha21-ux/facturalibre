"""Schemas Pydantic y canonicalización para facturas de compra."""

from __future__ import annotations

import hashlib
import json
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Annotated, Any, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.domain.models.purchase import PurchaseStatus

Money = Annotated[Decimal, Field(max_digits=18, decimal_places=2, ge=0)]
Quantity = Annotated[Decimal, Field(max_digits=18, decimal_places=4, gt=0)]
TaxRate = Annotated[Decimal, Field(max_digits=7, decimal_places=4, ge=0, le=100)]


class PurchaseLineCreate(BaseModel):
    """Datos de una línea al crear una factura de compra."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    item_id: UUID | None = None
    description: str = Field(min_length=1, max_length=500)
    quantity: Quantity
    unit_cost: Money
    tax_rate: TaxRate = Decimal("0")


class PurchaseCreate(BaseModel):
    """Datos para crear una factura de compra en borrador."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    supplier_id: UUID
    issue_date: date
    due_date: date
    lines: list[PurchaseLineCreate] = Field(min_length=1)
    cost_center_id: UUID | None = None

    @model_validator(mode="after")
    def validate_due_date(self) -> Self:
        """La fecha de vencimiento no puede ser anterior a la de emisión."""
        if self.due_date < self.issue_date:
            raise ValueError("due_date debe ser mayor o igual a issue_date")
        return self


class PurchaseLineRead(BaseModel):
    """Representación pública de una línea de compra."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    item_id: UUID | None
    description: str
    quantity: Decimal
    unit_cost: Decimal
    tax_rate: Decimal
    line_subtotal: Decimal
    line_tax: Decimal
    line_total: Decimal


class PurchaseRead(BaseModel):
    """Representación pública de una factura de compra con sus líneas."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    number: str | None
    supplier_id: UUID
    issue_date: date
    due_date: date
    status: PurchaseStatus
    subtotal: Decimal
    tax_total: Decimal
    total: Decimal
    balance: Decimal
    cost_center_id: UUID | None
    version: int
    created_at: datetime
    updated_at: datetime
    lines: list[PurchaseLineRead]


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


def canonical_body_hash(payload: PurchaseCreate) -> str:
    """Calcula SHA-256 del body normalizado, con claves ordenadas."""
    canonical = _canonicalize(payload.model_dump(mode="python"))
    encoded = json.dumps(
        canonical,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


class PurchasePaymentCreate(BaseModel):
    """Datos para registrar un pago a una factura de compra."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    amount: Money
    payment_date: date
    method: str = Field(min_length=1, max_length=50)
    reference: str | None = Field(default=None, max_length=100)


class PurchasePaymentRead(BaseModel):
    """Representación pública de un pago a compra."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    purchase_invoice_id: UUID
    amount: Decimal
    payment_date: date
    method: str
    reference: str | None
    created_at: datetime


def canonical_purchase_payment_hash(payload: PurchasePaymentCreate) -> str:
    """Calcula SHA-256 del body normalizado, con claves ordenadas."""
    canonical = _canonicalize(payload.model_dump(mode="python"))
    encoded = json.dumps(
        canonical,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
