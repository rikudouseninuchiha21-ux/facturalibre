"""Schemas Pydantic para presupuestos mensuales y el reporte Presupuesto vs Real."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, computed_field

from app.application.cost_center_schemas import CostCenterRead

# Los montos presupuestados pueden ser cero (cuenta reservada sin asignación).
BudgetMoney = Annotated[Decimal, Field(max_digits=18, decimal_places=2, ge=0)]


class BudgetLineCreate(BaseModel):
    """Datos para agregar una cuenta PUC al presupuesto."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    account_code: str = Field(min_length=1, max_length=20)
    amount: BudgetMoney
    notes: str | None = Field(default=None, max_length=2000)


class BudgetLineUpdate(BaseModel):
    """Datos parciales de una línea de presupuesto."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    amount: BudgetMoney | None = None
    notes: str | None = Field(default=None, max_length=2000)


class BudgetLineRead(BaseModel):
    """Línea presupuestada de una cuenta PUC."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    account_code: str
    account_name: str
    amount: Decimal
    notes: str | None


class BudgetCreate(BaseModel):
    """Datos para abrir un presupuesto mensual en estado DRAFT."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    cost_center_id: UUID
    period_year: int = Field(ge=2000, le=2100)
    period_month: int = Field(ge=1, le=12)
    name: str | None = Field(default=None, max_length=150)
    notes: str | None = Field(default=None, max_length=2000)


class BudgetUpdate(BaseModel):
    """Datos parciales de la cabecera del presupuesto (solo DRAFT)."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    name: str | None = Field(default=None, max_length=150)
    notes: str | None = Field(default=None, max_length=2000)


class BudgetRead(BaseModel):
    """Presupuesto con su centro de costo resumido y sus líneas."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    cost_center: CostCenterRead
    period_year: int
    period_month: int
    name: str | None
    status: str
    notes: str | None
    lines: list[BudgetLineRead]
    created_at: datetime
    updated_at: datetime

    @computed_field  # type: ignore[prop-decorator]
    @property
    def total(self) -> Decimal:
        """Suma de los montos presupuestados."""
        return sum((line.amount for line in self.lines), Decimal("0.00"))


class BudgetVsActualLine(BaseModel):
    """Comparación de lo presupuestado contra el gasto real de una cuenta."""

    account_code: str
    account_name: str
    budgeted: Decimal
    actual: Decimal
    variance: Decimal
    variance_pct: Decimal | None


class BudgetVsActualTotals(BaseModel):
    """Totales de control del bloque Presupuesto vs Real."""

    budgeted: Decimal
    actual: Decimal
    variance: Decimal
    variance_pct: Decimal | None


class BudgetVsActualResponse(BaseModel):
    """Reporte Presupuesto vs Real de un presupuesto concreto."""

    budget_id: UUID
    cost_center: CostCenterRead
    period_year: int
    period_month: int
    status: str
    lines: list[BudgetVsActualLine]
    totals: BudgetVsActualTotals


class BudgetVsActualReportResponse(BaseModel):
    """Reporte agregado: un bloque por presupuesto que matchea el filtro."""

    period_year: int
    period_month: int
    cost_center_id: UUID | None
    blocks: list[BudgetVsActualResponse]


__all__ = [
    "BudgetCreate",
    "BudgetLineCreate",
    "BudgetLineRead",
    "BudgetLineUpdate",
    "BudgetRead",
    "BudgetUpdate",
    "BudgetVsActualLine",
    "BudgetVsActualReportResponse",
    "BudgetVsActualResponse",
    "BudgetVsActualTotals",
]
