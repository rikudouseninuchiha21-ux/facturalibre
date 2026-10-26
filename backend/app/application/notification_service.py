"""Servicio de notificaciones in-app generadas por eventos del dominio.

El servicio no hace commit: las escrituras viven dentro de la misma
``operation_transaction`` que la operación de negocio que las dispara, de
modo que un fallo revierte también sus notificaciones (sin huérfanas).
"""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy.orm import Session

from app.domain.models.auth import UserRole
from app.domain.models.notification import Notification, NotificationSeverity
from app.domain.notification_repository import NotificationRepository


class NotificationService:
    """Creación y consulta de notificaciones por usuario."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.notifications = NotificationRepository(db)

    def create(
        self,
        *,
        user_id: UUID,
        category: str,
        severity: NotificationSeverity,
        title: str,
        body: str | None = None,
        link: str | None = None,
    ) -> Notification:
        """Crea una notificación para un usuario concreto."""
        return self.notifications.create(
            {
                "user_id": user_id,
                "category": category,
                "severity": severity,
                "title": title,
                "body": body,
                "link": link,
            }
        )

    def create_for_roles(
        self,
        *,
        roles: Sequence[UserRole],
        category: str,
        severity: NotificationSeverity,
        title: str,
        body: str | None = None,
        link: str | None = None,
    ) -> int:
        """Crea una notificación por cada usuario activo de los roles.

        Retorna cuántas notificaciones creó (una por usuario destino).
        """
        user_ids = self.notifications.active_user_ids_by_roles(list(roles))
        for user_id in user_ids:
            self.notifications.create(
                {
                    "user_id": user_id,
                    "category": category,
                    "severity": severity,
                    "title": title,
                    "body": body,
                    "link": link,
                }
            )
        return len(user_ids)

    def mark_read(self, *, notification_id: UUID, user_id: UUID) -> bool:
        """Marca una notificación como leída; solo si es del usuario."""
        return self.notifications.mark_read(
            notification_id=notification_id,
            user_id=user_id,
        )

    def mark_all_read(self, *, user_id: UUID) -> int:
        """Marca todas las no leídas del usuario y retorna cuántas marcó."""
        return self.notifications.mark_all_read(user_id=user_id)

    def unread_count(self, *, user_id: UUID) -> int:
        return self.notifications.unread_count(user_id=user_id)

    def list_for_user(
        self,
        *,
        user_id: UUID,
        unread_only: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Notification]:
        return self.notifications.list_for_user(
            user_id=user_id,
            unread_only=unread_only,
            limit=limit,
            offset=offset,
        )


__all__ = ["NotificationService"]
