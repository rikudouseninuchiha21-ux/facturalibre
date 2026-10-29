"""Casos de uso del CRM: embudo, oportunidades y actividades."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from sqlalchemy.orm import Session

from app.application.crm_schemas import (
    CrmActivityCreate,
    CrmOpportunityCreate,
    CrmOpportunityUpdate,
    CrmStageCreate,
    CrmStageUpdate,
)
from app.domain.company_repository import CompanyRepository
from app.domain.contact_repository import ContactRepository
from app.domain.crm_repository import CrmRepository
from app.domain.exceptions import (
    CrmStateError,
    CrmValidationError,
    ResourceNotFoundError,
)
from app.domain.models.crm import CrmActivity, CrmOpportunity, CrmStage
from app.domain.quote_repository import NewQuoteLine, QuoteRepository
from app.infrastructure.tenancy import require_company_id


class CrmService:
    """Reglas de negocio del embudo comercial."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.repository = CrmRepository(db)
        self.contacts = ContactRepository(db)
        self.companies = CompanyRepository(db)
        self.quotes = QuoteRepository(db)

    # -- Etapas ---------------------------------------------------------

    def list_stages(self) -> list[CrmStage]:
        """Etapas de la empresa activa."""
        return self.repository.list_stages()

    def create_stage(self, payload: CrmStageCreate) -> CrmStage:
        """Crea una etapa en la empresa activa."""
        stage = CrmStage(
            name=payload.name,
            order=payload.order,
            color=payload.color,
            is_won=payload.is_won,
            is_lost=payload.is_lost,
        )
        return self.repository.add_stage(stage)

    def update_stage(self, stage_id: UUID, payload: CrmStageUpdate) -> CrmStage:
        """Actualiza una etapa; gana/perdido son mutuamente excluyentes."""
        stage = self.repository.get_stage(stage_id)
        if stage is None:
            raise ResourceNotFoundError("Etapa no encontrada")

        values = payload.model_dump(exclude_unset=True)
        if values.get("is_won") is True:
            values["is_lost"] = False
        if values.get("is_lost") is True:
            values["is_won"] = False

        for key, value in values.items():
            setattr(stage, key, value)
        self.db.flush()
        self.db.refresh(stage)
        return stage

    def delete_stage(self, stage_id: UUID) -> None:
        """Elimina una etapa sin oportunidades asociadas."""
        stage = self.repository.get_stage(stage_id)
        if stage is None:
            raise ResourceNotFoundError("Etapa no encontrada")
        self.repository.delete_stage(stage)

    # -- Oportunidades --------------------------------------------------

    def list_opportunities(
        self,
        *,
        stage_id: UUID | None,
        limit: int,
        offset: int,
    ) -> list[CrmOpportunity]:
        """Oportunidades visibles en el Kanban."""
        return self.repository.list_opportunities(
            stage_id=stage_id,
            limit=limit,
            offset=offset,
        )

    def get_opportunity(
        self,
        opportunity_id: UUID,
        *,
        with_activities: bool = False,
    ) -> CrmOpportunity:
        """Oportunidad de la empresa activa o error 404."""
        opportunity = self.repository.get_opportunity(
            opportunity_id,
            with_activities=with_activities,
        )
        if opportunity is None:
            raise ResourceNotFoundError("Oportunidad no encontrada")
        return opportunity

    def _validate_contact(self, contact_id: UUID) -> None:
        contact = self.contacts.get_by_id(contact_id)
        if contact is None:
            raise CrmValidationError("contact_id no existe o está eliminado")

    def _validate_stage(self, stage_id: UUID) -> CrmStage:
        stage = self.repository.get_stage(stage_id)
        if stage is None:
            raise CrmValidationError("stage_id no existe para esta empresa")
        return stage

    def _validate_owner(self, owner_id: UUID) -> None:
        company_id = require_company_id(self.db)
        if self.companies.get_membership(owner_id, company_id) is None:
            raise CrmValidationError("owner_id no pertenece a esta empresa")

    def create_opportunity(
        self,
        payload: CrmOpportunityCreate,
        *,
        owner_id: UUID,
    ) -> CrmOpportunity:
        """Crea una oportunidad asignando la empresa activa automáticamente."""
        self._validate_contact(payload.contact_id)
        stage = self._validate_stage(payload.stage_id)
        self._validate_owner(owner_id)

        opportunity = CrmOpportunity(
            company_id=require_company_id(self.db),
            contact_id=payload.contact_id,
            stage_id=stage.id,
            owner_id=owner_id,
            title=payload.title,
            amount=payload.amount,
            expected_close_date=payload.expected_close_date,
            notes=payload.notes,
            is_won=stage.is_won,
            is_lost=stage.is_lost,
        )
        return self.repository.add_opportunity(opportunity)

    def update_opportunity(
        self,
        opportunity_id: UUID,
        payload: CrmOpportunityUpdate,
    ) -> CrmOpportunity:
        """Actualiza datos de la oportunidad y sincroniza el resultado."""
        opportunity = self.get_opportunity(opportunity_id)
        values = payload.model_dump(exclude_unset=True)

        if values.get("contact_id") is not None:
            self._validate_contact(values["contact_id"])
        if values.get("owner_id") is not None:
            self._validate_owner(values["owner_id"])
        if values.get("stage_id") is not None:
            stage = self._validate_stage(values["stage_id"])
            opportunity.is_won = stage.is_won
            opportunity.is_lost = stage.is_lost

        for key, value in values.items():
            setattr(opportunity, key, value)
        opportunity.updated_at = datetime.now(UTC)
        self.db.flush()
        self.db.refresh(opportunity)
        return opportunity

    def move_opportunity(self, opportunity_id: UUID, stage_id: UUID) -> CrmOpportunity:
        """Mueve la oportunidad y marca ganada/perdida según la etapa."""
        opportunity = self.get_opportunity(opportunity_id)
        stage = self._validate_stage(stage_id)

        opportunity.stage_id = stage.id
        opportunity.is_won = stage.is_won
        opportunity.is_lost = stage.is_lost
        opportunity.updated_at = datetime.now(UTC)
        self.db.flush()
        self.db.refresh(opportunity)
        return opportunity

    def delete_opportunity(self, opportunity_id: UUID) -> None:
        """Elimina una oportunidad y sus actividades."""
        opportunity = self.get_opportunity(opportunity_id)
        self.repository.delete_opportunity(opportunity)

    # -- Actividades ----------------------------------------------------

    def list_activities(self, opportunity_id: UUID) -> list[CrmActivity]:
        """Historial de la oportunidad."""
        self.get_opportunity(opportunity_id)
        return self.repository.list_activities(opportunity_id)

    def add_activity(
        self,
        opportunity_id: UUID,
        payload: CrmActivityCreate,
        *,
        created_by: UUID,
    ) -> CrmActivity:
        """Registra una llamada, correo, reunión o nota."""
        self.get_opportunity(opportunity_id)
        activity = CrmActivity(
            company_id=require_company_id(self.db),
            opportunity_id=opportunity_id,
            type=payload.type,
            description=payload.description,
            activity_date=payload.activity_date or datetime.now(UTC),
            created_by=created_by,
        )
        return self.repository.add_activity(activity)

    # -- Conversión -----------------------------------------------------

    def convert_to_quote(self, opportunity_id: UUID) -> CrmOpportunity:
        """Genera un borrador de cotización con los datos de la oportunidad."""
        opportunity = self.get_opportunity(opportunity_id)
        if opportunity.quote_id is not None:
            raise CrmStateError("La oportunidad ya tiene una cotización asociada")

        self._validate_contact(opportunity.contact_id)

        today = date.today()
        expiry_date = opportunity.expected_close_date
        if expiry_date is None or expiry_date < today:
            expiry_date = today + timedelta(days=30)

        amount = Decimal(opportunity.amount)
        line = NewQuoteLine(
            item_id=None,
            description=opportunity.title,
            quantity=Decimal("1"),
            unit_price=amount,
            tax_rate=Decimal("0"),
            subtotal=amount,
            tax=Decimal("0"),
            total=amount,
        )
        quote = self.quotes.create_draft(
            contact_id=opportunity.contact_id,
            issue_date=today,
            expiry_date=expiry_date,
            currency="COP",
            lines=[line],
            subtotal=amount,
            tax_total=Decimal("0"),
            total=amount,
        )
        opportunity.quote_id = quote.id
        opportunity.updated_at = datetime.now(UTC)
        self.db.flush()
        self.db.refresh(opportunity)
        return opportunity


__all__ = ["CrmService"]
