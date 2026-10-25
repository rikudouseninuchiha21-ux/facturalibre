"""Modelos del núcleo de nómina: empleados, periodos y detalle."""

from __future__ import annotations

import enum
import uuid
from datetime import date, datetime
from decimal import Decimal

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


class PayrollPeriodStatus(enum.StrEnum):
    """Ciclo de vida de un periodo de nómina."""

    DRAFT = "DRAFT"
    CLOSED = "CLOSED"


def _enum_values(enum_cls: type[enum.StrEnum]) -> list[str]:
    """Persiste los valores, no los nombres, de los enums."""
    return [member.value for member in enum_cls]


class Employee(Base):
    """Empleado activo o histórico de la empresa."""

    __tablename__ = "employees"

    __table_args__ = (CheckConstraint("base_salary > 0", name="ck_employees_base_salary_positive"),)

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    document: Mapped[str] = mapped_column(String(30), nullable=False, unique=True)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str | None] = mapped_column(String(255))
    base_salary: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
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

    payroll_details: Mapped[list[PayrollDetail]] = relationship(back_populates="employee")


class PayrollPeriod(Base):
    """Periodo mensual de liquidación de nómina."""

    __tablename__ = "payroll_periods"

    __table_args__ = (
        UniqueConstraint("month", "year", name="uq_payroll_periods_month_year"),
        CheckConstraint("month BETWEEN 1 AND 12", name="ck_payroll_periods_month_range"),
        CheckConstraint("year BETWEEN 2000 AND 2100", name="ck_payroll_periods_year_range"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    month: Mapped[int] = mapped_column(Integer, nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[PayrollPeriodStatus] = mapped_column(
        Enum(
            PayrollPeriodStatus,
            name="payroll_period_status",
            native_enum=True,
            values_callable=_enum_values,
        ),
        nullable=False,
        default=PayrollPeriodStatus.DRAFT,
        server_default=text("'DRAFT'"),
        index=True,
    )
    # Dimensión opcional de centro de costo; se propaga al asiento de nómina.
    cost_center_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("cost_centers.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
        comment="Centro de costo al que se atribuye la liquidación de nómina.",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    details: Mapped[list[PayrollDetail]] = relationship(
        back_populates="period",
        cascade="all, delete-orphan",
        order_by="PayrollDetail.employee_id",
    )


class PayrollDetail(Base):
    """Liquidación de un empleado dentro de un periodo de nómina."""

    __tablename__ = "payroll_details"

    __table_args__ = (
        UniqueConstraint(
            "period_id",
            "employee_id",
            name="uq_payroll_details_period_id_employee_id",
        ),
        CheckConstraint(
            "base_salary > 0",
            name="ck_payroll_details_base_salary_positive",
        ),
        CheckConstraint(
            "health_deduction >= 0",
            name="ck_payroll_details_health_deduction_non_negative",
        ),
        CheckConstraint(
            "pension_deduction >= 0",
            name="ck_payroll_details_pension_deduction_non_negative",
        ),
        CheckConstraint("net_pay >= 0", name="ck_payroll_details_net_pay_non_negative"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    period_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("payroll_periods.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    employee_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("employees.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    base_salary: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    health_deduction: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    pension_deduction: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    net_pay: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    period: Mapped[PayrollPeriod] = relationship(back_populates="details")
    employee: Mapped[Employee] = relationship(back_populates="payroll_details")

    @property
    def employee_name(self) -> str:
        """Nombre completo del empleado para la representación pública."""
        return f"{self.employee.first_name} {self.employee.last_name}"

    @property
    def employee_document(self) -> str:
        """Documento del empleado para la representación pública."""
        return self.employee.document
