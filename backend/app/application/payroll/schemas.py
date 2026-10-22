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
    created_at: datetime


class PayrollPeriodCreate(BaseModel):
    """Datos para abrir un periodo mensual de nómina."""

    model_config = ConfigDict(extra="forbid")

    month: int = Field(ge=1, le=12)
    year: int = Field(ge=2000, le=2100)


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
