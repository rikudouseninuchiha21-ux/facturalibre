"""Schemas Pydantic del módulo de nómina."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Self
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    computed_field,
    model_validator,
)

from app.domain.models.invoice import DianDocumentStatus
from app.domain.models.payroll import PayrollPeriodStatus

Salary = Annotated[Decimal, Field(max_digits=18, decimal_places=2, gt=0)]
Money = Annotated[Decimal, Field(max_digits=18, decimal_places=2, ge=0)]


class EmployeeCreate(BaseModel):
    """Datos para crear un empleado."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    document: str = Field(min_length=1, max_length=30)
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    email: EmailStr | None = None
    base_salary: Salary
    start_date: date
    is_active: bool = True

    # -- Fase 39A: datos fiscales para la Nómina Electrónica.
    document_type: str | None = Field(default=None, max_length=10)
    birth_date: date | None = None
    address: str | None = Field(default=None, max_length=200)
    municipality_code: str | None = Field(default=None, max_length=5)
    department_code: str | None = Field(default=None, max_length=2)
    contract_type: str | None = Field(default=None, max_length=20)
    salary_type: str | None = Field(default=None, max_length=20)
    risk_level: str | None = Field(default=None, max_length=5)
    bank_account: str | None = Field(default=None, max_length=50)
    afp_code: str | None = Field(default=None, max_length=20)
    eps_code: str | None = Field(default=None, max_length=20)
    arl_code: str | None = Field(default=None, max_length=20)
    severance_fund_code: str | None = Field(default=None, max_length=20)
    compensation_fund_code: str | None = Field(default=None, max_length=20)


class EmployeeUpdate(BaseModel):
    """Actualización parcial de un empleado."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    document: str | None = Field(default=None, min_length=1, max_length=30)
    first_name: str | None = Field(default=None, min_length=1, max_length=100)
    last_name: str | None = Field(default=None, min_length=1, max_length=100)
    email: EmailStr | None = None
    base_salary: Salary | None = None
    start_date: date | None = None
    is_active: bool | None = None

    # -- Fase 39A: datos fiscales para la Nómina Electrónica.
    document_type: str | None = Field(default=None, max_length=10)
    birth_date: date | None = None
    address: str | None = Field(default=None, max_length=200)
    municipality_code: str | None = Field(default=None, max_length=5)
    department_code: str | None = Field(default=None, max_length=2)
    contract_type: str | None = Field(default=None, max_length=20)
    salary_type: str | None = Field(default=None, max_length=20)
    risk_level: str | None = Field(default=None, max_length=5)
    bank_account: str | None = Field(default=None, max_length=50)
    afp_code: str | None = Field(default=None, max_length=20)
    eps_code: str | None = Field(default=None, max_length=20)
    arl_code: str | None = Field(default=None, max_length=20)
    severance_fund_code: str | None = Field(default=None, max_length=20)
    compensation_fund_code: str | None = Field(default=None, max_length=20)

    @model_validator(mode="after")
    def validate_update_fields(self) -> Self:
        """Evita updates vacíos y valores nulos en campos obligatorios."""
        if not self.model_fields_set:
            raise ValueError("Debe enviar al menos un campo editable")
        required_fields = (
            "document",
            "first_name",
            "last_name",
            "base_salary",
            "start_date",
            "is_active",
        )
        for field in required_fields:
            if field in self.model_fields_set and getattr(self, field) is None:
                raise ValueError(f"{field} no puede ser null")
        return self


class EmployeeRead(BaseModel):
    """Representación pública de un empleado."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    document: str
    first_name: str
    last_name: str
    email: EmailStr | None
    base_salary: Decimal
    start_date: date
    is_active: bool
    document_type: str | None = None
    birth_date: date | None = None
    address: str | None = None
    municipality_code: str | None = None
    department_code: str | None = None
    contract_type: str | None = None
    salary_type: str | None = None
    risk_level: str | None = None
    bank_account: str | None = None
    afp_code: str | None = None
    eps_code: str | None = None
    arl_code: str | None = None
    severance_fund_code: str | None = None
    compensation_fund_code: str | None = None
    created_at: datetime


class PayrollPeriodCreate(BaseModel):
    """Datos para abrir un periodo mensual de nómina."""

    model_config = ConfigDict(extra="forbid")

    month: int = Field(ge=1, le=12)
    year: int = Field(ge=2000, le=2100)
    cost_center_id: UUID | None = None


class PayrollDetailRead(BaseModel):
    """Liquidación individual de un empleado."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    period_id: UUID
    employee_id: UUID
    employee_name: str
    employee_document: str
    base_salary: Money
    health_deduction: Money
    pension_deduction: Money
    net_pay: Money
    created_at: datetime


class PayrollPeriodRead(BaseModel):
    """Periodo de nómina con su detalle y totales de control."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    month: int
    year: int
    status: PayrollPeriodStatus
    dian_cune: str | None = None
    dian_status: DianDocumentStatus | None = None
    payment_date: date | None = None
    cost_center_id: UUID | None
    created_at: datetime
    details: list[PayrollDetailRead]

    @computed_field  # type: ignore[prop-decorator]
    @property
    def total_base(self) -> Decimal:
        """Total devengado del periodo."""
        return sum((detail.base_salary for detail in self.details), Decimal("0.00"))

    @computed_field  # type: ignore[prop-decorator]
    @property
    def total_health(self) -> Decimal:
        """Total deducido por salud."""
        return sum((detail.health_deduction for detail in self.details), Decimal("0.00"))

    @computed_field  # type: ignore[prop-decorator]
    @property
    def total_pension(self) -> Decimal:
        """Total deducido por pensión."""
        return sum((detail.pension_deduction for detail in self.details), Decimal("0.00"))

    @computed_field  # type: ignore[prop-decorator]
    @property
    def total_net(self) -> Decimal:
        """Total neto a pagar a los empleados."""
        return sum((detail.net_pay for detail in self.details), Decimal("0.00"))
