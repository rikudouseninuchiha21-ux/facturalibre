"""Rutas de notificaciones in-app del usuario autenticado."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.api.dependencies.auth import CurrentUser, get_current_user
from app.application.notification_schemas import (
    MarkAllReadResponse,
    NotificationRead,
    UnreadCountResponse,
)
from app.application.notification_service import NotificationService
from app.domain.notification_repository import NotificationRepository
from app.infrastructure.database import get_db
from app.infrastructure.transactions import operation_transaction

router = APIRouter(
    prefix="/notifications",
    tags=["notifications"],
    # Cualquier usuario autenticado tiene notificaciones propias.
    dependencies=[Depends(get_current_user)],
)

DbSession = Annotated[Session, Depends(get_db)]


def get_notification_repository(db: DbSession) -> NotificationRepository:
    """Construye el repositorio con la sesión de la petición."""
    return NotificationRepository(db)


NotificationRepositoryDep = Annotated[
    NotificationRepository,
    Depends(get_notification_repository),
]


def get_notification_service(db: DbSession) -> NotificationService:
    """Construye el servicio de notificaciones con la sesión de la petición."""
    return NotificationService(db)


NotificationServiceDep = Annotated[
    NotificationService,
    Depends(get_notification_service),
]


@router.get("", response_model=list[NotificationRead])
def list_notifications(
    current_user: CurrentUser,
    service: NotificationServiceDep,
    unread_only: Annotated[bool, Query()] = False,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[NotificationRead]:
    """Lista las notificaciones del usuario actual, nunca las de otros."""
    notifications = service.list_for_user(
        user_id=current_user.id,
        unread_only=unread_only,
        limit=limit,
        offset=offset,
    )
    return [NotificationRead.model_validate(item) for item in notifications]


@router.get("/unread-count", response_model=UnreadCountResponse)
def get_unread_count(
    current_user: CurrentUser,
    service: NotificationServiceDep,
) -> UnreadCountResponse:
    """Cantidad de notificaciones no leídas del usuario actual."""
    return UnreadCountResponse(count=service.unread_count(user_id=current_user.id))


@router.post(
    "/{notification_id}/mark-read",
    status_code=status.HTTP_204_NO_CONTENT,
)
def mark_notification_read(
    notification_id: UUID,
    current_user: CurrentUser,
    db: DbSession,
    service: NotificationServiceDep,
) -> Response:
    """Marca una notificación como leída; 404 si es de otro usuario."""
    with operation_transaction(db):
        marked = service.mark_read(
            notification_id=notification_id,
            user_id=current_user.id,
        )
    if not marked:
        return Response(status_code=status.HTTP_404_NOT_FOUND)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/mark-all-read", response_model=MarkAllReadResponse)
def mark_all_notifications_read(
    current_user: CurrentUser,
    db: DbSession,
    service: NotificationServiceDep,
) -> MarkAllReadResponse:
    """Marca todas las notificaciones del usuario actual como leídas."""
    with operation_transaction(db):
        marked = service.mark_all_read(user_id=current_user.id)
    return MarkAllReadResponse(marked=marked)


__all__ = ["router"]
