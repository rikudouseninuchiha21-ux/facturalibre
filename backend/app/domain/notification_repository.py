"""Repositorio de notificaciones in-app con SQLAlchemy 2.

El repositorio nunca confirma transacciones; la capa de API agrupa las
escrituras con ``operation_transaction``.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.models.auth import UserRole
from app.domain.models.notification import Notification


class NotificationRepository:
    """Acceso a datos de notificaciones, siempre filtrado por usuario."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, values: dict[str, Any]) -> Notification:
        """Crea una notificación sin confirmar la transacción."""
        notification = Notification(**values)
        self.db.add(notification)
        self.db.flush()
        self.db.refresh(notification)
        return notification

    def get_by_id(self, notification_id: UUID) -> Notification | None:
        return self.db.scalar(select(Notification).where(Notification.id == notification_id))

    def list_for_user(
        self,
        *,
        user_id: UUID,
        unread_only: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Notification]:
        statement = (
            select(Notification)
            .where(Notification.user_id == user_id)
            .order_by(Notification.created_at.desc(), Notification.id)
            .limit(limit)
            .offset(offset)
        )
        if unread_only:
            statement = statement.where(Notification.read_at.is_(None))
        return list(self.db.scalars(statement).all())

    def mark_read(self, *, notification_id: UUID, user_id: UUID) -> bool:
        """Marca una notificación como leída solo si pertenece al usuario.

        Se muta la entidad (y no un UPDATE suelto) para mantener el identity
        map consistente con las lecturas posteriores de la misma sesión.
        """
        notification = self.db.scalar(
            select(Notification).where(
                Notification.id == notification_id,
                Notification.user_id == user_id,
            )
        )
        if notification is None or notification.read_at is not None:
            return False
        notification.read_at = datetime.now(UTC)
        self.db.flush()
        return True

    def mark_all_read(self, *, user_id: UUID) -> int:
        """Marca todas las notificaciones no leídas del usuario."""
        unread = self.db.scalars(
            select(Notification).where(
                Notification.user_id == user_id,
                Notification.read_at.is_(None),
            )
        ).all()
        now = datetime.now(UTC)
        for notification in unread:
            notification.read_at = now
        self.db.flush()
        return len(unread)

    def unread_count(self, *, user_id: UUID) -> int:
        statement = (
            select(Notification.id)
            .where(
                Notification.user_id == user_id,
                Notification.read_at.is_(None),
            )
            .limit(1000)
        )
        return len(self.db.scalars(statement).all())

    def active_user_ids_by_roles(self, roles: list[UserRole]) -> list[UUID]:
        """Identificadores de los usuarios activos con los roles indicados."""
        from app.domain.models.auth import User

        statement = select(User.id).where(
            User.role.in_(roles),
            User.is_active.is_(True),
        )
        return list(self.db.scalars(statement).all())


__all__ = ["NotificationRepository"]
