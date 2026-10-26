"""Schemas Pydantic para notificaciones in-app."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.domain.models.notification import NotificationSeverity


class NotificationRead(BaseModel):
    """Representación pública de una notificación."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    category: str
    severity: NotificationSeverity
    title: str
    body: str | None
    link: str | None
    read_at: datetime | None
    created_at: datetime


class UnreadCountResponse(BaseModel):
    """Cantidad de notificaciones no leídas del usuario actual."""

    count: int


class MarkAllReadResponse(BaseModel):
    """Cantidad de notificaciones marcadas como leídas."""

    marked: int


__all__ = [
    "MarkAllReadResponse",
    "NotificationRead",
    "UnreadCountResponse",
]
