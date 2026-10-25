"""Schemas Pydantic y canonicalización para pagos."""

from __future__ import annotations

import hashlib
import json
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Annotated, Any, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

PaymentAmount = Annotated[Decimal, Field(max_digits=18, decimal_places=2, gt=0)]


class PaymentCreate(BaseModel):
    """Datos para registrar un pago sobre una factura emitida."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    amount: PaymentAmount
    payment_date: date
    # REQUIERE VALIDACIÓN: contador/experto DIAN. El catálogo de medios de pago
    # será un enum controlado en una fase posterior; en el MVP es texto libre.
    method: str = Field(min_length=1, max_length=50)
    reference: str | None = Field(default=None, max_length=100)

    @model_validator(mode="after")
    def validate_payment_date(self) -> Self:
        """Un pago no puede registrarse con fecha futura."""
        if self.payment_date > date.today():
            raise ValueError("payment_date no puede ser futura")
        return self


class PaymentRead(BaseModel):
    """Representación pública de un pago."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    invoice_id: UUID
    amount: Decimal
    payment_date: date
    method: str
    reference: str | None
    bank_movement_id: UUID | None
    created_at: datetime


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


def canonical_payment_hash(payload: PaymentCreate) -> str:
    """Calcula SHA-256 del body normalizado, con claves ordenadas."""
    canonical = _canonicalize(payload.model_dump(mode="python"))
    encoded = json.dumps(
        canonical,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
