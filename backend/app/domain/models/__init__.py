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
    FiscalPeriod,
    FiscalPeriodStatus,
)
from app.domain.models.auth import AuthSession, User, UserRole
from app.domain.models.bank import (
    BankAccount,
    BankAccountType,
    BankTransaction,
    BankTransactionType,
)
from app.domain.models.company_setting import CompanySetting
from app.domain.models.contact import Contact, ContactStatus, ContactType
from app.domain.models.credit_note import CreditNote, CreditNoteLine, CreditNoteStatus
from app.domain.models.expense import Expense
from app.domain.models.fixed_asset import DepreciationEntry, FixedAsset, FixedAssetStatus
from app.domain.models.idempotency_key import IdempotencyKey
from app.domain.models.invoice import Invoice, LifecycleStatus, PaymentStatus
from app.domain.models.invoice_line import InvoiceLine
from app.domain.models.item import Item
from app.domain.models.number_sequence import NumberSequence
from app.domain.models.payment import Payment
from app.domain.models.payroll import (
    Employee,
    PayrollDetail,
    PayrollPeriod,
    PayrollPeriodStatus,
)
from app.domain.models.purchase import (
    PurchaseInvoice,
    PurchaseLine,
    PurchasePayment,
    PurchaseStatus,
)
from app.domain.models.quote import Quote, QuoteStatus
from app.domain.models.quote_line import QuoteLine
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
    "AuthSession",
    "BankAccount",
    "BankAccountType",
    "BankTransaction",
    "BankTransactionType",
    "CompanySetting",
    "Contact",
    "ContactStatus",
    "ContactType",
    "CreditNote",
    "CreditNoteLine",
    "CreditNoteStatus",
    "DepreciationEntry",
    "Employee",
    "Expense",
    "FiscalPeriod",
    "FixedAsset",
    "FixedAssetStatus",
    "FiscalPeriodStatus",
    "IdempotencyKey",
    "Invoice",
    "InvoiceLine",
    "Item",
    "LifecycleStatus",
    "NumberSequence",
    "Payment",
    "PaymentStatus",
    "PayrollDetail",
    "PayrollPeriod",
    "PayrollPeriodStatus",
    "PurchaseInvoice",
    "PurchaseLine",
    "PurchasePayment",
    "PurchaseStatus",
    "Quote",
    "QuoteLine",
    "QuoteStatus",
    "StockBalance",
    "StockMovement",
    "StockMovementType",
    "Tax",
    "User",
    "UserRole",
    "Warehouse",
]
