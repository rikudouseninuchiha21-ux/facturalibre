"""Modelos del CRM: embudo, oportunidades y actividades."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    Uuid,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.domain.models.tenancy import CompanyScopedMixin
from app.infrastructure.database import Base

if TYPE_CHECKING:
    from app.domain.models.auth import User
    from app.domain.models.contact import Contact


class CrmStage(CompanyScopedMixin, Base):
    """Etapa configurable del embudo de ventas."""

    __tablename__ = "crm_stages"

    __table_args__ = (
        CheckConstraint(
            "NOT (is_won AND is_lost)",
            name="ck_crm_stages_one_outcome",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    order: Mapped[int] = mapped_column("order", Integer, nullable=False, index=True)
    color: Mapped[str] = mapped_column(String(7), nullable=False, server_default=text("'#7c3aed'"))
    is_won: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )
    is_lost: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
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


class CrmOpportunity(CompanyScopedMixin, Base):
    """Oportunidad de venta que avanza por el embudo."""

    __tablename__ = "crm_opportunities"

    __table_args__ = (
        CheckConstraint("amount >= 0", name="ck_crm_opportunities_amount_non_negative"),
        CheckConstraint(
            "NOT (is_won AND is_lost)",
            name="ck_crm_opportunities_one_outcome",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    contact_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("contacts.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    stage_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("crm_stages.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    amount: Mapped[Decimal] = mapped_column(
        Numeric(18, 2), nullable=False, server_default=text("0")
    )
    expected_close_date: Mapped[date | None] = mapped_column(Date)
    owner_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    notes: Mapped[str | None] = mapped_column(Text)
    quote_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("quotes.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    invoice_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("invoices.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    is_won: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )
    is_lost: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
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

    contact: Mapped[Contact] = relationship()
    stage: Mapped[CrmStage] = relationship()
    owner: Mapped[User] = relationship()
    activities: Mapped[list[CrmActivity]] = relationship(
        back_populates="opportunity",
        cascade="all, delete-orphan",
        order_by="CrmActivity.activity_date.desc()",
    )

    @property
    def contact_name(self) -> str:
        """Nombre del contacto para la representación pública."""
        return self.contact.name

    @property
    def stage_name(self) -> str:
        """Nombre de la etapa actual."""
        return self.stage.name

    @property
    def owner_name(self) -> str:
        """Nombre del responsable comercial."""
        return self.owner.full_name


class CrmActivity(CompanyScopedMixin, Base):
    """Interacción registrada sobre una oportunidad."""

    __tablename__ = "crm_activities"

    __table_args__ = (
        CheckConstraint(
            "type IN ('CALL', 'EMAIL', 'MEETING', 'NOTE')",
            name="ck_crm_activities_type",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    opportunity_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("crm_opportunities.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    type: Mapped[str] = mapped_column(String(20), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    activity_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), index=True
    )
    created_by: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    opportunity: Mapped[CrmOpportunity] = relationship(back_populates="activities")
    creator: Mapped[User] = relationship()

    @property
    def created_by_name(self) -> str:
        """Nombre del usuario que registró la actividad."""
        return self.creator.full_name


__all__ = ["CrmActivity", "CrmOpportunity", "CrmStage"]
