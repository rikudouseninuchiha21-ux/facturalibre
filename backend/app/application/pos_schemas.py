"""Schemas de respuesta del punto de venta."""

from __future__ import annotations

from pydantic import BaseModel

from app.application.invoice_schemas import InvoiceRead
from app.application.payment_schemas import PaymentRead


class PosCheckoutRead(BaseModel):
    """Resultado atómico de una venta en el POS.

    La factura ya está emitida y, si tuvo total positivo, pagada en efectivo.
    ``payment`` es ``None`` solo para facturas de total cero, que no admiten un
    pago con monto positivo.
    """

    invoice: InvoiceRead
    payment: PaymentRead | None
