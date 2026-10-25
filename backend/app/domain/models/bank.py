"""Modelos de bancos y tesorería: cuentas bancarias y movimientos.

Los movimientos son inmutables: para corregir un error se registra un
movimiento compensatorio, no se edita el original. La conciliación solo marca
el movimiento como revisado contra el extracto bancario.
"""

from __future__ import annotations

import enum
import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Enum,
    ForeignKey,
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

if TYPE_CHECKING:
    from app.domain.models.accounting import AccountingAccount


class BankAccountType(enum.StrEnum):
    """Tipo de producto bancario."""

    CHECKING = "CHECKING"
    SAVINGS = "SAVINGS"


class BankTransactionType(enum.StrEnum):
    """Efecto de un movimiento sobre las cuentas de tesorería."""

    DEPOSIT = "DEPOSIT"
    WITHDRAWAL = "WITHDRAWAL"
    TRANSFER = "TRANSFER"


def _enum_values(enum_cls: type[enum.StrEnum]) -> list[str]:
    """Persiste los valores, no los nombres, de los enums."""
    return [member.value for member in enum_cls]


class BankAccount(Base):
    """Cuenta bancaria de la empresa.

    ``accounting_account_code`` apunta a la cuenta auxiliar del PUC que
    representa esta cuenta en el libro mayor. Dos cuentas bancarias pueden
    compartir código PUC, pero una transferencia entre ellas exige códigos
    distintos para que el asiento tenga efecto contable real.
    """

    __tablename__ = "bank_accounts"

    __table_args__ = (
        UniqueConstraint(
            "bank_name",
            "account_number",
            name="uq_bank_accounts_bank_name_account_number",
        ),
        CheckConstraint("currency = 'COP'", name="ck_bank_accounts_currency_cop"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    bank_name: Mapped[str] = mapped_column(String(100), nullable=False)
    account_number: Mapped[str] = mapped_column(String(50), nullable=False)
    account_type: Mapped[BankAccountType] = mapped_column(
        Enum(
            BankAccountType,
            name="bank_account_type",
            native_enum=True,
            values_callable=_enum_values,
        ),
        nullable=False,
        default=BankAccountType.CHECKING,
        server_default=text("'CHECKING'"),
    )
    currency: Mapped[str] = mapped_column(
        String(3),
        nullable=False,
        default="COP",
        server_default=text("'COP'"),
        comment="MVP solo COP.",
    )
    accounting_account_code: Mapped[str] = mapped_column(
        String(20),
        ForeignKey("accounting_accounts.code", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("true"),
        index=True,
    )
    version: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1, server_default=text("1")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    accounting_account: Mapped[AccountingAccount] = relationship()
    transactions: Mapped[list[BankTransaction]] = relationship(
        back_populates="bank_account",
        foreign_keys="BankTransaction.bank_account_id",
    )

    @property
    def accounting_account_name(self) -> str:
        """Nombre de la cuenta PUC asociada, para la representación pública."""
        return self.accounting_account.name


class BankTransaction(Base):
    """Movimiento bancario inmutable.

    - ``DEPOSIT``: entra dinero a la cuenta. Débito al banco, crédito a la
      cuenta de contrapartida (ingreso, por cobrar, etc.).
    - ``WITHDRAWAL``: sale dinero de la cuenta. Débito a la contrapartida,
      crédito al banco.
    - ``TRANSFER``: traslado entre dos cuentas de la empresa. Débito a la
      cuenta destino, crédito a la cuenta origen. Se registra una sola fila y
      aplica a ambas cuentas para conciliación.
    """

    __tablename__ = "bank_transactions"

    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_bank_transactions_amount_positive"),
        CheckConstraint(
            """
            (
                transaction_type = 'TRANSFER'
                AND counterpart_account_id IS NOT NULL
                AND counterpart_account_code IS NULL
                AND counterpart_account_id <> bank_account_id
            )
            OR
            (
                transaction_type IN ('DEPOSIT', 'WITHDRAWAL')
                AND counterpart_account_id IS NULL
                AND counterpart_account_code IS NOT NULL
            )
            """,
            name="ck_bank_transactions_counterpart",
        ),
        CheckConstraint(
            """
            (is_reconciled = false AND reconciled_at IS NULL)
            OR (is_reconciled = true AND reconciled_at IS NOT NULL)
            """,
            name="ck_bank_transactions_reconciliation_consistency",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    bank_account_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("bank_accounts.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    counterpart_account_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("bank_accounts.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    transaction_type: Mapped[BankTransactionType] = mapped_column(
        Enum(
            BankTransactionType,
            name="bank_transaction_type",
            native_enum=True,
            values_callable=_enum_values,
        ),
        nullable=False,
        index=True,
    )
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    description: Mapped[str] = mapped_column(String(200), nullable=False)
    reference: Mapped[str | None] = mapped_column(String(100))
    counterpart_account_code: Mapped[str | None] = mapped_column(
        String(20),
        ForeignKey("accounting_accounts.code", ondelete="RESTRICT"),
        index=True,
    )
    is_reconciled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("false"),
        index=True,
    )
    reconciled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    version: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1, server_default=text("1")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    bank_account: Mapped[BankAccount] = relationship(
        back_populates="transactions",
        foreign_keys=[bank_account_id],
    )
    counterpart_account: Mapped[BankAccount | None] = relationship(
        foreign_keys=[counterpart_account_id],
    )

    @property
    def bank_account_name(self) -> str:
        """Nombre de la cuenta origen del movimiento."""
        return self.bank_account.name

    @property
    def counterpart_account_name(self) -> str | None:
        """Nombre de la cuenta destino en una transferencia."""
        if self.counterpart_account is None:
            return None
        return self.counterpart_account.name


__all__ = [
    "BankAccount",
    "BankAccountType",
    "BankTransaction",
    "BankTransactionType",
]
