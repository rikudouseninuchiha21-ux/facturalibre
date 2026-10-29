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

from app.domain.models.invoice import DianDocumentStatus
from app.domain.models.tenancy import CompanyScopedMixin
from app.infrastructure.database import Base


class PayrollPeriodStatus(enum.StrEnum):
    """Ciclo de vida de un periodo de nómina."""

    DRAFT = "DRAFT"
    CLOSED = "CLOSED"


def _enum_values(enum_cls: type[enum.StrEnum]) -> list[str]:
    """Persiste los valores, no los nombres, de los enums."""
    return [member.value for member in enum_cls]


class Employee(CompanyScopedMixin, Base):
    """Empleado activo o histórico de la empresa."""

    __tablename__ = "employees"

    __table_args__ = (
        UniqueConstraint("company_id", "document", name="uq_employees_company_document"),
        CheckConstraint("base_salary > 0", name="ck_employees_base_salary_positive"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    document: Mapped[str] = mapped_column(String(30), nullable=False)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str | None] = mapped_column(String(255))
    base_salary: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)

    # -- Fase 39A: datos fiscales para la Nómina Electrónica (Dec. 1601/2020).
    # ``document`` ya es el número: aquí va el tipo (CC, CE, NIT, PA).
    document_type: Mapped[str | None] = mapped_column(String(10))
    birth_date: Mapped[date | None] = mapped_column(Date)
    address: Mapped[str | None] = mapped_column(String(200))
    municipality_code: Mapped[str | None] = mapped_column(String(5))
    department_code: Mapped[str | None] = mapped_column(String(2))
    contract_type: Mapped[str | None] = mapped_column(String(20))
    salary_type: Mapped[str | None] = mapped_column(String(20))
    # Nivel de riesgo ARL: I, II, III, IV o V.
    risk_level: Mapped[str | None] = mapped_column(String(5))
    bank_account: Mapped[str | None] = mapped_column(String(50))
    afp_code: Mapped[str | None] = mapped_column(String(20))
    eps_code: Mapped[str | None] = mapped_column(String(20))
    arl_code: Mapped[str | None] = mapped_column(String(20))
    severance_fund_code: Mapped[str | None] = mapped_column(String(20))
    compensation_fund_code: Mapped[str | None] = mapped_column(String(20))
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


class PayrollPeriod(CompanyScopedMixin, Base):
    """Periodo mensual de liquidación de nómina."""

    __tablename__ = "payroll_periods"

    __table_args__ = (
        UniqueConstraint(
            "company_id",
            "month",
            "year",
            name="uq_payroll_periods_company_month_year",
        ),
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
    # -- Fase 39A: documento electrónico de nómina.
    dian_cune: Mapped[str | None] = mapped_column(String(96))
    dian_status: Mapped[DianDocumentStatus | None] = mapped_column(
        Enum(
            DianDocumentStatus,
            name="dian_document_status",
            native_enum=True,
            values_callable=_enum_values,
        ),
        nullable=True,
        index=True,
    )
    xml_generated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    payment_date: Mapped[date | None] = mapped_column(Date)
    notes_dian: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    details: Mapped[list[PayrollDetail]] = relationship(
        back_populates="period",
        cascade="all, delete-orphan",
        order_by="PayrollDetail.employee_id",
    )


class PayrollDetail(CompanyScopedMixin, Base):
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
    contribution: Mapped[PayrollContribution | None] = relationship(
        back_populates="detail", uselist=False
    )

    @property
    def employee_name(self) -> str:
        """Nombre completo del empleado para la representación pública."""
        return f"{self.employee.first_name} {self.employee.last_name}"

    @property
    def employee_document(self) -> str:
        """Documento del empleado para la representación pública."""
        return self.employee.document


class PayrollContribution(CompanyScopedMixin, Base):
    """Aportes y prestaciones de un empleado dentro de un periodo de nómina.

    Una fila por ``PayrollDetail`` (1:1). Solo persisten los aportes del
    empleador y las provisiones; las deducciones del empleado (salud y
    pensión 4 %) ya viven en ``PayrollDetail``.
    """

    __tablename__ = "payroll_contributions"

    __table_args__ = (
        CheckConstraint("health_employer >= 0", name="ck_payroll_contributions_health_employer"),
        CheckConstraint("health_employee >= 0", name="ck_payroll_contributions_health_employee"),
        CheckConstraint("pension_employer >= 0", name="ck_payroll_contributions_pension_employer"),
        CheckConstraint("pension_employee >= 0", name="ck_payroll_contributions_pension_employee"),
        CheckConstraint("arl_employer >= 0", name="ck_payroll_contributions_arl"),
        CheckConstraint(
            "compensation_fund >= 0", name="ck_payroll_contributions_compensation_fund"
        ),
        CheckConstraint("icbf >= 0", name="ck_payroll_contributions_icbf"),
        CheckConstraint("sena >= 0", name="ck_payroll_contributions_sena"),
        CheckConstraint("severance >= 0", name="ck_payroll_contributions_severance"),
        CheckConstraint(
            "severance_interest >= 0", name="ck_payroll_contributions_severance_interest"
        ),
        CheckConstraint("vacation >= 0", name="ck_payroll_contributions_vacation"),
        CheckConstraint("bonus >= 0", name="ck_payroll_contributions_bonus"),
        Index("ix_payroll_contributions_period_id", "period_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    payroll_detail_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("payroll_details.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    # Denormalizado para consultar aportes por periodo sin JOIN.
    period_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("payroll_periods.id", ondelete="CASCADE"), nullable=False
    )
    health_employee: Mapped[Decimal] = mapped_column(
        Numeric(18, 2), nullable=False, default=Decimal("0.00"), server_default=text("0")
    )
    health_employer: Mapped[Decimal] = mapped_column(
        Numeric(18, 2), nullable=False, default=Decimal("0.00"), server_default=text("0")
    )
    pension_employee: Mapped[Decimal] = mapped_column(
        Numeric(18, 2), nullable=False, default=Decimal("0.00"), server_default=text("0")
    )
    pension_employer: Mapped[Decimal] = mapped_column(
        Numeric(18, 2), nullable=False, default=Decimal("0.00"), server_default=text("0")
    )
    arl_employer: Mapped[Decimal] = mapped_column(
        Numeric(18, 2), nullable=False, default=Decimal("0.00"), server_default=text("0")
    )
    compensation_fund: Mapped[Decimal] = mapped_column(
        Numeric(18, 2), nullable=False, default=Decimal("0.00"), server_default=text("0")
    )
    icbf: Mapped[Decimal] = mapped_column(
        Numeric(18, 2), nullable=False, default=Decimal("0.00"), server_default=text("0")
    )
    sena: Mapped[Decimal] = mapped_column(
        Numeric(18, 2), nullable=False, default=Decimal("0.00"), server_default=text("0")
    )
    severance: Mapped[Decimal] = mapped_column(
        Numeric(18, 2), nullable=False, default=Decimal("0.00"), server_default=text("0")
    )
    severance_interest: Mapped[Decimal] = mapped_column(
        Numeric(18, 2), nullable=False, default=Decimal("0.00"), server_default=text("0")
    )
    vacation: Mapped[Decimal] = mapped_column(
        Numeric(18, 2), nullable=False, default=Decimal("0.00"), server_default=text("0")
    )
    bonus: Mapped[Decimal] = mapped_column(
        Numeric(18, 2), nullable=False, default=Decimal("0.00"), server_default=text("0")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    detail: Mapped[PayrollDetail] = relationship(back_populates="contribution")

    @property
    def total_employer_contributions(self) -> Decimal:
        """Aportes a cargo del empleador (excluye provisiones)."""
        return (
            self.health_employer
            + self.pension_employer
            + self.arl_employer
            + self.compensation_fund
            + self.icbf
            + self.sena
        )


__all__ = [
    "Employee",
    "PayrollContribution",
    "PayrollDetail",
    "PayrollPeriod",
    "PayrollPeriodStatus",
]
