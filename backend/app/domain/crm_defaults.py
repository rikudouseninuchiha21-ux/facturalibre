"""Etapas iniciales del embudo CRM para cada empresa."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.models.crm import CrmStage

DEFAULT_CRM_STAGES: tuple[tuple[str, int, str, bool, bool], ...] = (
    ("Nuevo Lead", 1, "#94a3b8", False, False),
    ("Contactado", 2, "#3b82f6", False, False),
    ("Propuesta", 3, "#8b5cf6", False, False),
    ("Negociación", 4, "#f59e0b", False, False),
    ("Ganado", 5, "#10b981", True, False),
    ("Perdido", 6, "#ef4444", False, True),
)


def seed_default_stages(db: Session, company_id: UUID) -> None:
    """Crea las seis etapas estándar si la empresa aún no tiene ninguna."""
    exists = db.scalar(select(CrmStage.id).where(CrmStage.company_id == company_id).limit(1))
    if exists is not None:
        return

    for name, order, color, is_won, is_lost in DEFAULT_CRM_STAGES:
        db.add(
            CrmStage(
                company_id=company_id,
                name=name,
                order=order,
                color=color,
                is_won=is_won,
                is_lost=is_lost,
            )
        )
    db.flush()
