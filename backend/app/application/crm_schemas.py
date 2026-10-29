"""Schemas Pydantic del CRM y del embudo de ventas."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Literal, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

Money = Annotated[Decimal, Field(max_digits=18, decimal_places=2, ge=0)]
ActivityType = Literal["CALL", "EMAIL", "MEETING", "NOTE"]
HEX_COLOR = r"^#[0-9a-fA-F]{6}$"


class CrmStageCreate(BaseModel):
    """Datos para crear una etapa del embudo."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    name: str = Field(min_length=1, max_length=100)
    order: int = Field(ge=0)
    color: str = Field(default="#7c3aed", pattern=HEX_COLOR)
    is_won: bool = False
    is_lost: bool = False

    @model_validator(mode="after")
    def validate_outcome(self) -> Self:
        """Una etapa no puede ser ganada y perdida a la vez."""
        if self.is_won and self.is_lost:
            raise ValueError("Una etapa no puede ser is_won e is_lost a la vez")
        return self


class CrmStageUpdate(BaseModel):
    """Actualización parcial de una etapa."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=100)
    order: int | None = Field(default=None, ge=0)
    color: str | None = Field(default=None, pattern=HEX_COLOR)
    is_won: bool | None = None
    is_lost: bool | None = None

    @model_validator(mode="after")
    def validate_outcome(self) -> Self:
        """Rechaza la combinación explícita ganada + perdida."""
        if self.is_won is True and self.is_lost is True:
            raise ValueError("Una etapa no puede ser is_won e is_lost a la vez")
        return self


class CrmStageRead(BaseModel):
    """Representación pública de una etapa."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    order: int
    color: str
    is_won: bool
    is_lost: bool


class CrmOpportunityCreate(BaseModel):
    """Datos para crear una oportunidad."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    contact_id: UUID
    stage_id: UUID
    owner_id: UUID | None = None
    title: str = Field(min_length=1, max_length=200)
    amount: Money = Decimal("0.00")
    expected_close_date: date | None = None
    notes: str | None = Field(default=None, max_length=5000)


class CrmOpportunityUpdate(BaseModel):
    """Actualización parcial de una oportunidad."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    contact_id: UUID | None = None
    stage_id: UUID | None = None
    owner_id: UUID | None = None
    title: str | None = Field(default=None, min_length=1, max_length=200)
    amount: Money | None = None
    expected_close_date: date | None = None
    notes: str | None = Field(default=None, max_length=5000)


class CrmMoveRequest(BaseModel):
    """Movimiento de una oportunidad a otra etapa del Kanban."""

    model_config = ConfigDict(extra="forbid")

    stage_id: UUID


class CrmActivityCreate(BaseModel):
    """Registro de una interacción con el cliente."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    type: ActivityType
    description: str = Field(min_length=1, max_length=5000)
    activity_date: datetime | None = None


class CrmActivityRead(BaseModel):
    """Representación pública de una actividad."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    opportunity_id: UUID
    type: str
    description: str
    activity_date: datetime
    created_by: UUID
    created_by_name: str
    created_at: datetime


class CrmOpportunityRead(BaseModel):
    """Representación pública de una oportunidad."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    contact_id: UUID
    contact_name: str
    stage_id: UUID
    stage_name: str
    owner_id: UUID
    owner_name: str
    title: str
    amount: Decimal
    expected_close_date: date | None
    notes: str | None
    quote_id: UUID | None
    invoice_id: UUID | None
    is_won: bool
    is_lost: bool
    created_at: datetime
    updated_at: datetime


class CrmOpportunityDetailRead(CrmOpportunityRead):
    """Oportunidad con su historial de actividades."""

    activities: list[CrmActivityRead]
