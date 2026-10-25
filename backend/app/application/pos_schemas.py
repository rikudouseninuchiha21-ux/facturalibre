"""Schemas del punto de venta."""

from __future__ import annotations

from datetime import date
from typing import Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.application.invoice_schemas import (
    Currency,
    InvoiceLineCreate,
    InvoiceRead,
)
from app.application.payment_schemas import PaymentRead


class PosCheckoutCreate(BaseModel):
    """Datos para cobrar una venta en el POS.

    ``contact_id`` es opcional porque el POS permite vender a "Consumidor
    Final". El endpoint resuelve o crea el contacto genérico antes de crear la
    factura. También se acepta cadena vacía para tolerar clientes antiguos que
    enviaban ``""`` en lugar de ``null``.
    """

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    contact_id: UUID | None = None
    issue_date: date
    due_date: date
    currency: Currency = "COP"
    lines: list[InvoiceLineCreate] = Field(min_length=1)

    @field_validator("contact_id", mode="before")
    @classmethod
    def blank_contact_id_as_none(cls, value: object) -> object:
        """Normaliza el string vacío a ``None`` antes de validar el UUID."""
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @model_validator(mode="after")
    def validate_due_date(self) -> Self:
        """La fecha de vencimiento no puede ser anterior a la de emisión."""
        # Mantiene la misma regla que InvoiceCreate para no aceptar una venta
        # que luego sería rechazada al construir la factura normal.
        if self.due_date < self.issue_date:
            raise ValueError("due_date debe ser mayor o igual a issue_date")
        return self


class PosCheckoutRead(BaseModel):
    """Resultado atómico de una venta en el POS.

    La factura ya está emitida y, si tuvo total positivo, pagada en efectivo.
    ``payment`` es ``None`` solo para facturas de total cero, que no admiten un
    pago con monto positivo.
    """

    invoice: InvoiceRead
    payment: PaymentRead | None
