"""Schemas Pydantic para cartera, recordatorios y acuerdos de pago."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.domain.models.receivables import AgreementStatus, ReminderChannel

Money = Annotated[Decimal, Field(max_digits=18, decimal_places=2)]
PositiveMoney = Annotated[Decimal, Field(max_digits=18, decimal_places=2, gt=0)]


# -- Aging -----------------------------------------------------------------


class AgingBuckets(BaseModel):
    """Totales por rango de vencimiento."""

    current: Decimal
    d0_30: Decimal
    d31_60: Decimal
    d61_90: Decimal
    d91_120: Decimal
    d120_plus: Decimal
    total: Decimal


class CustomerAging(BaseModel):
    """Aging agregado de un cliente."""

    contact_id: UUID
    contact_name: str
    current: Decimal
    d0_30: Decimal
    d31_60: Decimal
    d61_90: Decimal
    d91_120: Decimal
    d120_plus: Decimal
    total: Decimal
    total_overdue: Decimal
    invoice_count: int


class AgingReport(BaseModel):
    """Reporte de aging a una fecha de corte."""

    as_of_date: date
    buckets_totals: AgingBuckets
    by_customer: list[CustomerAging]
    total_overdue: Decimal


class ReceivablesSummary(BaseModel):
    """Resumen global de cartera con el top de clientes deudores."""

    as_of_date: date
    buckets_totals: AgingBuckets
    total_overdue: Decimal
    top_customers: list[CustomerAging]
    customer_count: int


# -- Estado de cuenta ------------------------------------------------------


StatementLineType = Literal["INVOICE", "PAYMENT", "CREDIT_NOTE"]


class StatementLine(BaseModel):
    """Movimiento del estado de cuenta con saldo corrido."""

    date: date
    type: StatementLineType
    reference: str
    description: str
    debit: Decimal
    credit: Decimal
    running_balance: Decimal


class CustomerStatement(BaseModel):
    """Estado de cuenta de un cliente en un rango de fechas."""

    contact_id: UUID
    contact_name: str
    from_date: date
    to_date: date
    opening_balance: Decimal
    lines: list[StatementLine]
    closing_balance: Decimal


# -- Recordatorios ---------------------------------------------------------


class ReminderCreate(BaseModel):
    """Datos para registrar un recordatorio de cobranza."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    invoice_id: UUID
    level: int = Field(ge=1, le=5)
    channel: ReminderChannel = ReminderChannel.IN_APP
    notes: str | None = Field(default=None, max_length=2000)


class ReminderRead(BaseModel):
    """Recordatorio persistido."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    invoice_id: UUID
    contact_id: UUID
    level: int
    channel: ReminderChannel
    sent_at: datetime
    notes: str | None
    created_by: UUID
    created_at: datetime


class AutoRemindRequest(BaseModel):
    """Fecha de corte opcional para el job manual de recordatorios."""

    model_config = ConfigDict(extra="forbid")

    as_of_date: date | None = None


class AutoRemindResult(BaseModel):
    """Resultado idempotente del job de recordatorios automáticos."""

    created: int
    skipped: int
    errors: int


# -- Acuerdos de pago ------------------------------------------------------


class AgreementCreate(BaseModel):
    """Datos para crear un acuerdo de pago y generar sus cuotas."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    contact_id: UUID
    invoice_id: UUID | None = None
    total_amount: PositiveMoney
    installments: int = Field(ge=1, le=120)
    start_date: date
    frequency_days: int = Field(default=30, ge=1, le=365)
    notes: str | None = Field(default=None, max_length=2000)


class InstallmentRead(BaseModel):
    """Cuota de un acuerdo con su saldo derivado."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    due_date: date
    amount: Decimal
    paid_amount: Decimal
    paid_at: datetime | None
    balance: Decimal


class AgreementRead(BaseModel):
    """Acuerdo de pago con sus cuotas."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    contact_id: UUID
    invoice_id: UUID | None
    total_amount: Decimal
    installments: int
    start_date: date
    status: AgreementStatus
    notes: str | None
    created_by: UUID
    created_at: datetime
    updated_at: datetime
    installment_items: list[InstallmentRead]
    paid_total: Decimal
    balance: Decimal


class InstallmentPayRequest(BaseModel):
    """Monto a registrar como pago de una cuota."""

    model_config = ConfigDict(extra="forbid")

    amount: PositiveMoney


__all__ = [
    "AgreementCreate",
    "AgreementRead",
    "AgingBuckets",
    "AutoRemindRequest",
    "AutoRemindResult",
    "CustomerAging",
    "CustomerStatement",
    "InstallmentPayRequest",
    "InstallmentRead",
    "ReceivablesSummary",
    "ReminderCreate",
    "ReminderRead",
    "StatementLine",
    "StatementLineType",
]
