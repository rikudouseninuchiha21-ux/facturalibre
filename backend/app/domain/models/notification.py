"""Modelo de notificaciones in-app por usuario."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    Index,
    String,
    Text,
    Uuid,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.database import Base

if TYPE_CHECKING:
    from app.domain.models.auth import User


class NotificationSeverity(enum.StrEnum):
    """Severidad de la notificación para su presentación en la UI."""

    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


def _enum_values(enum_cls: type[enum.StrEnum]) -> list[str]:
    """Persiste los valores, no los nombres, de los enums."""
    return [member.value for member in enum_cls]


class Notification(Base):
    """Notificación in-app dirigida a un usuario concreto.

    El cuerpo es texto plano (nunca se renderiza como HTML) y ``link`` es una
    ruta relativa de la app (por ejemplo ``/budgets/<id>``).
    """

    __tablename__ = "notifications"

    __table_args__ = (
        Index("ix_notifications_user_read_at", "user_id", "read_at"),
        Index("ix_notifications_user_created", "user_id", "created_at"),
        Index("ix_notifications_created_at", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    category: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    severity: Mapped[NotificationSeverity] = mapped_column(
        Enum(
            NotificationSeverity,
            name="notification_severity",
            native_enum=True,
            values_callable=_enum_values,
        ),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    body: Mapped[str | None] = mapped_column(Text)
    link: Mapped[str | None] = mapped_column(String(500))
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    user: Mapped[User] = relationship()


__all__ = ["Notification", "NotificationSeverity"]
