"""Acceso a datos del CRM: etapas, oportunidades y actividades."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.domain.models.crm import CrmActivity, CrmOpportunity, CrmStage


class CrmRepository:
    """Consultas y persistencia del embudo comercial."""

    def __init__(self, db: Session) -> None:
        self.db = db

    # -- Etapas ---------------------------------------------------------

    def list_stages(self) -> list[CrmStage]:
        """Etapas ordenadas según el tablero Kanban."""
        statement = select(CrmStage).order_by(CrmStage.order, CrmStage.name)
        return list(self.db.scalars(statement).all())

    def get_stage(self, stage_id: UUID) -> CrmStage | None:
        """Busca una etapa de la empresa activa."""
        return self.db.scalar(select(CrmStage).where(CrmStage.id == stage_id))

    def add_stage(self, stage: CrmStage) -> CrmStage:
        """Agrega una etapa a la transacción actual."""
        self.db.add(stage)
        self.db.flush()
        self.db.refresh(stage)
        return stage

    def delete_stage(self, stage: CrmStage) -> None:
        """Elimina una etapa; las oportunidades referenciadas la bloquean."""
        self.db.delete(stage)
        self.db.flush()

    # -- Oportunidades --------------------------------------------------

    def list_opportunities(
        self,
        *,
        stage_id: UUID | None,
        limit: int,
        offset: int,
    ) -> list[CrmOpportunity]:
        """Oportunidades de la empresa activa, con sus relaciones visibles."""
        statement = (
            select(CrmOpportunity)
            .options(
                selectinload(CrmOpportunity.contact),
                selectinload(CrmOpportunity.stage),
                selectinload(CrmOpportunity.owner),
            )
            .order_by(CrmOpportunity.updated_at.desc(), CrmOpportunity.id)
            .limit(limit)
            .offset(offset)
        )
        if stage_id is not None:
            statement = statement.where(CrmOpportunity.stage_id == stage_id)
        return list(self.db.scalars(statement).all())

    def get_opportunity(
        self,
        opportunity_id: UUID,
        *,
        with_activities: bool = False,
    ) -> CrmOpportunity | None:
        """Busca una oportunidad de la empresa activa."""
        options = [
            selectinload(CrmOpportunity.contact),
            selectinload(CrmOpportunity.stage),
            selectinload(CrmOpportunity.owner),
        ]
        if with_activities:
            options.append(
                selectinload(CrmOpportunity.activities).selectinload(CrmActivity.creator)
            )
        statement = (
            select(CrmOpportunity).where(CrmOpportunity.id == opportunity_id).options(*options)
        )
        return self.db.scalar(statement)

    def add_opportunity(self, opportunity: CrmOpportunity) -> CrmOpportunity:
        """Agrega una oportunidad a la transacción actual."""
        self.db.add(opportunity)
        self.db.flush()
        self.db.refresh(opportunity)
        return opportunity

    def delete_opportunity(self, opportunity: CrmOpportunity) -> None:
        """Elimina una oportunidad y su historial."""
        self.db.delete(opportunity)
        self.db.flush()

    # -- Actividades ----------------------------------------------------

    def list_activities(self, opportunity_id: UUID) -> list[CrmActivity]:
        """Historial de actividades de una oportunidad."""
        statement = (
            select(CrmActivity)
            .where(CrmActivity.opportunity_id == opportunity_id)
            .options(selectinload(CrmActivity.creator))
            .order_by(CrmActivity.activity_date.desc(), CrmActivity.created_at.desc())
        )
        return list(self.db.scalars(statement).all())

    def add_activity(self, activity: CrmActivity) -> CrmActivity:
        """Registra una actividad en la transacción actual."""
        self.db.add(activity)
        self.db.flush()
        self.db.refresh(activity)
        return activity
