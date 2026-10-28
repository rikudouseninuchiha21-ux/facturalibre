"""Modelo de consentimientos GDPR/CCPA (Fase 39B)."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, Uuid, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database import Base


class UserConsent(Base):
    """Registro de consentimiento: quién, qué y cuándo (inmutable)."""

    __tablename__ = "user_consents"

    __table_args__ = (
        Index("ix_user_consents_user_id", "user_id"),
        Index("ix_user_consents_consent_type", "consent_type"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()")
    )
    # Nullable: los visitantes anónimos también consienten cookies.
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    ip_address: Mapped[str | None] = mapped_column(String(45))
    user_agent: Mapped[str | None] = mapped_column(String(255))
    consent_type: Mapped[str] = mapped_column(String(30), nullable=False)
    is_granted: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=text("true")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


__all__ = ["UserConsent"]
