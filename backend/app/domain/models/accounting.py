"""Modelos del núcleo contable: catálogo PUC, asientos y movimientos."""

from __future__ import annotations

import enum
import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    Uuid,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.database import Base


class AccountType(enum.StrEnum):
    """Clasificación de cuentas del Plan Único de Cuentas (PUC)."""

    ACTIVO = "ACTIVO"
    PASIVO = "PASIVO"
    PATRIMONIO = "PATRIMONIO"
    INGRESO = "INGRESO"
    GASTO = "GASTO"
    COSTO = "COSTO"


class AccountNature(enum.StrEnum):
    """Naturaleza de saldo normal de una cuenta PUC."""

    DEBITO = "DEBITO"
    CREDITO = "CREDITO"


class AccountingSourceType(enum.StrEnum):
    """Evento de facturación que originó el asiento."""

    INVOICE = "INVOICE"
    PAYMENT = "PAYMENT"
    PURCHASE = "PURCHASE"
    PURCHASE_PAYMENT = "PURCHASE_PAYMENT"
    CREDIT_NOTE = "CREDIT_NOTE"
    VOID = "VOID"
    PAYMENT_REVERSAL = "PAYMENT_REVERSAL"
    PAYROLL = "PAYROLL"
    EXPENSE = "EXPENSE"
    EXPENSE_REVERSAL = "EXPENSE_REVERSAL"
    BANK_TRANSACTION = "BANK_TRANSACTION"
    DEPRECIATION = "DEPRECIATION"


class AccountingEntryStatus(enum.StrEnum):
    """Estado del comprobante contable."""

    DRAFT = "DRAFT"
    POSTED = "POSTED"


class FiscalPeriodStatus(enum.StrEnum):
    """Estado de bloqueo contable de un mes calendario."""

    OPEN = "OPEN"
    CLOSED = "CLOSED"


def _enum_values(enum_cls: type[enum.StrEnum]) -> list[str]:
    """Persiste los valores, no los nombres, de los enums."""
    return [member.value for member in enum_cls]


class AccountingAccount(Base):
    """Cuenta del catálogo jerárquico PUC.

    El código es la PK natural porque el PUC se identifica por su código
    (por ejemplo, 130505). ``parent_code`` permite construir la jerarquía.
    """

    __tablename__ = "accounting_accounts"

    code: Mapped[str] = mapped_column(String(20), primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    account_type: Mapped[AccountType] = mapped_column(
        Enum(
            AccountType,
            name="accounting_account_type",
            native_enum=True,
            values_callable=_enum_values,
        ),
        nullable=False,
        index=True,
    )
    nature: Mapped[AccountNature] = mapped_column(
        Enum(
            AccountNature,
            name="accounting_account_nature",
            native_enum=True,
            values_callable=_enum_values,
        ),
        nullable=False,
    )
    parent_code: Mapped[str | None] = mapped_column(
        String(20),
        ForeignKey("accounting_accounts.code", ondelete="RESTRICT"),
        index=True,
    )

    parent: Mapped[AccountingAccount | None] = relationship(
        back_populates="children",
        remote_side="AccountingAccount.code",
    )
    children: Mapped[list[AccountingAccount]] = relationship(back_populates="parent")
    entry_lines: Mapped[list[AccountingEntryLine]] = relationship(back_populates="account")


class AccountingEntry(Base):
    """Asiento o comprobante contable de partida doble."""

    __tablename__ = "accounting_entries"

    __table_args__ = (
        UniqueConstraint(
            "source_type",
            "source_id",
            name="uq_accounting_entries_source_type_source_id",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    entry_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    source_type: Mapped[AccountingSourceType] = mapped_column(
        Enum(
            AccountingSourceType,
            name="accounting_entry_source_type",
            native_enum=True,
            values_callable=_enum_values,
        ),
        nullable=False,
        index=True,
    )
    # Polimórfico: puede apuntar a invoices.id o payments.id según source_type.
    source_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False, index=True)
    status: Mapped[AccountingEntryStatus] = mapped_column(
        Enum(
            AccountingEntryStatus,
            name="accounting_entry_status",
            native_enum=True,
            values_callable=_enum_values,
        ),
        nullable=False,
        default=AccountingEntryStatus.POSTED,
        server_default=text("'POSTED'"),
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    lines: Mapped[list[AccountingEntryLine]] = relationship(
        back_populates="entry",
        cascade="all, delete-orphan",
        order_by="AccountingEntryLine.account_code",
    )


class AccountingEntryLine(Base):
    """Movimiento débito/crédito de un asiento."""

    __tablename__ = "accounting_entry_lines"

    __table_args__ = (
        CheckConstraint("debit >= 0", name="ck_accounting_entry_lines_debit_non_negative"),
        CheckConstraint("credit >= 0", name="ck_accounting_entry_lines_credit_non_negative"),
        CheckConstraint(
            "(debit > 0 AND credit = 0) OR (credit > 0 AND debit = 0)",
            name="ck_accounting_entry_lines_one_side_positive",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    entry_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("accounting_entries.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    account_code: Mapped[str] = mapped_column(
        String(20),
        ForeignKey("accounting_accounts.code", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    debit: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, server_default=text("0"))
    credit: Mapped[Decimal] = mapped_column(
        Numeric(18, 2), nullable=False, server_default=text("0")
    )

    entry: Mapped[AccountingEntry] = relationship(back_populates="lines")
    account: Mapped[AccountingAccount] = relationship(back_populates="entry_lines")

    @property
    def account_name(self) -> str:
        """Nombre de la cuenta para la representación pública del movimiento."""
        return self.account.name


class FiscalPeriod(Base):
    """Periodo contable mensual.

    La ausencia de fila equivale a un periodo abierto. La fila se crea cuando
    se cierra el mes para conservar la fecha y hora del cierre. Una vez que el
    estado es ``CLOSED``, el servicio contable rechaza nuevos asientos con
    fecha dentro de ese mes.
    """

    __tablename__ = "fiscal_periods"

    __table_args__ = (
        CheckConstraint("month >= 1 AND month <= 12", name="ck_fiscal_periods_month_range"),
        CheckConstraint("year >= 2000", name="ck_fiscal_periods_year_min"),
        UniqueConstraint("month", "year", name="uq_fiscal_periods_month_year"),
        Index("ix_fiscal_periods_year_month", "year", "month"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    month: Mapped[int] = mapped_column(Integer, nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[FiscalPeriodStatus] = mapped_column(
        Enum(
            FiscalPeriodStatus,
            name="fiscal_period_status",
            native_enum=True,
            values_callable=_enum_values,
        ),
        nullable=False,
        default=FiscalPeriodStatus.OPEN,
        server_default=text("'OPEN'"),
    )
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
