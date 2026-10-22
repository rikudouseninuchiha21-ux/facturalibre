"""Schemas Pydantic y canonicalización para facturas."""

from __future__ import annotations

import hashlib
import json
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Annotated, Any, Literal, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.domain.models.invoice import LifecycleStatus, PaymentStatus

Money = Annotated[Decimal, Field(max_digits=18, decimal_places=2, ge=0)]
Quantity = Annotated[Decimal, Field(max_digits=18, decimal_places=4, gt=0)]
DiscountPercent = Annotated[Decimal, Field(max_digits=5, decimal_places=2, ge=0, le=100)]
TaxRate = Annotated[Decimal, Field(max_digits=7, decimal_places=4, ge=0, le=100)]
# REQUIERE VALIDACIÓN: contador/experto DIAN. MVP solo COP; multimoneda y
# reglas de conversión quedan para una fase posterior.
Currency = Literal["COP"]


class InvoiceLineCreate(BaseModel):
    """Datos de una línea al crear una factura."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    item_id: UUID
    description: str | None = None
    quantity: Quantity
    unit_price: Money
    discount_percent: DiscountPercent = Decimal("0")
    tax_rate: TaxRate | None = None


class InvoiceCreate(BaseModel):
    """Datos para crear una factura en borrador."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    contact_id: UUID
    issue_date: date
    due_date: date
    currency: Currency = "COP"
    lines: list[InvoiceLineCreate] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_due_date(self) -> Self:
        """La fecha de vencimiento no puede ser anterior a la de emisión."""
        if self.due_date < self.issue_date:
            raise ValueError("due_date debe ser mayor o igual a issue_date")
        return self


class VoidInvoiceRequest(BaseModel):
    """Motivo obligatorio para anular una factura emitida."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    reason: str = Field(min_length=1, max_length=500)


class InvoiceLineRead(BaseModel):
    """Representación pública de una línea de factura."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    item_id: UUID | None
    description: str
    quantity: Decimal
    unit_price: Decimal
    discount_percent: Decimal
    tax_rate: Decimal
    line_subtotal: Decimal
    line_tax: Decimal
    line_total: Decimal


class InvoiceRead(BaseModel):
    """Representación pública de una factura con sus líneas."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    number: str | None
    contact_id: UUID
    issue_date: date
    due_date: date
    currency: str
    lifecycle_status: LifecycleStatus
    payment_status: PaymentStatus
    voided_reason: str | None
    voided_at: datetime | None
    subtotal: Decimal
    tax_total: Decimal
    total: Decimal
    balance: Decimal
    version: int
    created_at: datetime
    updated_at: datetime
    lines: list[InvoiceLineRead]


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


def canonical_body_hash(payload: InvoiceCreate) -> str:
    """Calcula SHA-256 del body normalizado, con claves ordenadas."""
    canonical = _canonicalize(payload.model_dump(mode="python"))
    encoded = json.dumps(
        canonical,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
