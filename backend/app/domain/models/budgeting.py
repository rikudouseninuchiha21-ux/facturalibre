"""Modelos de centros de costo y presupuestos mensuales por cuenta PUC."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.database import Base

if TYPE_CHECKING:
    from app.domain.models.accounting import AccountingAccount


class BudgetStatus(enum.StrEnum):
    """Ciclo de vida de un presupuesto mensual."""

    DRAFT = "DRAFT"
    APPROVED = "APPROVED"
    CLOSED = "CLOSED"


def _enum_values(enum_cls: type[enum.StrEnum]) -> list[str]:
    """Persiste los valores, no los nombres, de los enums."""
    return [member.value for member in enum_cls]


class CostCenter(Base):
    """Centro de costo (Ventas, Administración, Producción, etc.).

    Dimensión contable opcional: los asientos pueden etiquetarse con un
    centro de costo para atribuir gastos y costos por área de la empresa.
    """

    __tablename__ = "cost_centers"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    code: Mapped[str] = mapped_column(String(20), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("true"),
        index=True,
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


class Budget(Base):
    """Presupuesto mensual de un centro de costo.

    Un presupuesto agrupa líneas por cuenta PUC. Solo se puede editar en
    estado DRAFT; al aprobarse queda inmutable y al cerrarse marca el fin
    del ciclo de control presupuestal del mes.
    """

    __tablename__ = "budgets"

    __table_args__ = (
        UniqueConstraint(
            "cost_center_id",
            "period_year",
            "period_month",
            name="uq_budgets_cost_center_period",
        ),
        CheckConstraint("period_month BETWEEN 1 AND 12", name="ck_budgets_month_range"),
        CheckConstraint(
            "period_year BETWEEN 2000 AND 2100",
            name="ck_budgets_year_range",
        ),
        Index("ix_budgets_period", "period_year", "period_month"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    cost_center_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("cost_centers.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    period_year: Mapped[int] = mapped_column(Integer, nullable=False)
    period_month: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str | None] = mapped_column(String(150))
    status: Mapped[BudgetStatus] = mapped_column(
        Enum(
            BudgetStatus,
            name="budget_status",
            native_enum=True,
            values_callable=_enum_values,
        ),
        nullable=False,
        default=BudgetStatus.DRAFT,
        server_default=text("'DRAFT'"),
        index=True,
    )
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    cost_center: Mapped[CostCenter] = relationship()
    lines: Mapped[list[BudgetLine]] = relationship(
        back_populates="budget",
        cascade="all, delete-orphan",
        order_by="BudgetLine.account_code",
    )


class BudgetLine(Base):
    """Monto presupuestado para una cuenta PUC dentro de un presupuesto."""

    __tablename__ = "budget_lines"

    __table_args__ = (
        CheckConstraint("amount >= 0", name="ck_budget_lines_amount_non_negative"),
        UniqueConstraint("budget_id", "account_code", name="uq_budget_lines_budget_account"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    budget_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("budgets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # La tabla PUC del proyecto (accounting_accounts) tiene código VARCHAR
    # como clave primaria, no un identificador UUID.
    account_code: Mapped[str] = mapped_column(
        String(20),
        ForeignKey("accounting_accounts.code", ondelete="RESTRICT"),
        nullable=False,
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    budget: Mapped[Budget] = relationship(back_populates="lines")
    account: Mapped[AccountingAccount] = relationship()

    @property
    def account_name(self) -> str:
        """Nombre de la cuenta PUC para la representación pública."""
        if self.account is not None:
            return self.account.name
        return self.account_code


__all__ = [
    "Budget",
    "BudgetLine",
    "BudgetStatus",
    "CostCenter",
]
