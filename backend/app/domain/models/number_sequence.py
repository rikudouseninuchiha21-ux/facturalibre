"""Modelo de secuencias de numeración."""

from __future__ import annotations

import uuid

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Integer,
    String,
    UniqueConstraint,
    Uuid,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.domain.models.tenancy import CompanyScopedMixin
from app.infrastructure.database import Base


class NumberSequence(CompanyScopedMixin, Base):
    __tablename__ = "number_sequences"

    __table_args__ = (
        UniqueConstraint("company_id", "name", name="uq_number_sequences_company_name"),
        CheckConstraint("next_number > 0", name="ck_number_sequences_next_number_positive"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    prefix: Mapped[str] = mapped_column(String(20), nullable=False)
    next_number: Mapped[int] = mapped_column(
        BigInteger, nullable=False, default=1, server_default=text("1")
    )
    version: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1, server_default=text("1")
    )
