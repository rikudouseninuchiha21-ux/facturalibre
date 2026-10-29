"""Mixin común para las entidades aisladas por empresa."""

from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, Uuid
from sqlalchemy.orm import Mapped, mapped_column


class CompanyScopedMixin:
    """Agrega la empresa propietaria a una entidad de negocio.

    El filtro global de sesión usa este mixin para restringir automáticamente
    todas las consultas ORM a la empresa activa. El valor se asigna al hacer
    *flush* si la entidad no lo trae explícito.
    """

    company_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("companies.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
