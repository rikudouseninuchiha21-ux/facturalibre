"""Modelos de dominio de FacturaLibre.

Importar este paquete registra todas las tablas en ``Base.metadata``.
"""

from app.domain.models.accounting import (
    AccountingAccount,
    AccountingEntry,
    AccountingEntryLine,
    AccountingEntryStatus,
    AccountingSourceType,
    AccountNature,
    AccountType,
)
from app.domain.models.contact import Contact
from app.domain.models.idempotency_key import IdempotencyKey
from app.domain.models.invoice import Invoice, LifecycleStatus, PaymentStatus
from app.domain.models.invoice_line import InvoiceLine
from app.domain.models.item import Item
from app.domain.models.number_sequence import NumberSequence
from app.domain.models.payment import Payment
from app.domain.models.stock import StockBalance, StockMovement, StockMovementType
from app.domain.models.tax import Tax
from app.domain.models.warehouse import Warehouse

__all__ = [
    "AccountingAccount",
    "AccountingEntry",
    "AccountingEntryLine",
    "AccountingEntryStatus",
    "AccountingSourceType",
    "AccountNature",
    "AccountType",
    "Contact",
    "IdempotencyKey",
    "Invoice",
    "InvoiceLine",
    "Item",
    "LifecycleStatus",
    "NumberSequence",
    "Payment",
    "PaymentStatus",
    "StockBalance",
    "StockMovement",
    "StockMovementType",
    "Tax",
    "Warehouse",
]
