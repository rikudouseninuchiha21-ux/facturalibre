"""Rutas de gestión de usuarios (solo administrador)."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies.auth import CurrentUser, get_current_user, require_role
from app.application.auth.service import AuthService
from app.application.user_schemas import (
    UserCreate,
    UserRead,
    UserUpdate,
)
from app.domain.exceptions import EmailAlreadyRegisteredError
from app.domain.models.auth import UserRole
from app.infrastructure.database import get_db

router = APIRouter(
    prefix="/users",
    tags=["users"],
    dependencies=[
        Depends(get_current_user),
        Depends(require_role([UserRole.ADMIN])),
    ],
)

DbSession = Annotated[Session, Depends(get_db)]


def get_auth_service(db: DbSession) -> AuthService:
    """Construye el servicio de autenticación."""
    return AuthService(db)


AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]


@router.get("", response_model=list[UserRead])
def list_users(
    service: AuthServiceDep,
) -> list[UserRead]:
    """Lista todos los usuarios registrados (solo ADMIN)."""
    users = service.repository.list_users()
    return [UserRead.model_validate(u) for u in users]


@router.post("", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def create_user(
    payload: UserCreate,
    service: AuthServiceDep,
) -> UserRead:
    """Crea un nuevo usuario (solo ADMIN)."""
    try:
        user = service.create_user(payload)
    except EmailAlreadyRegisteredError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    return UserRead.model_validate(user)


@router.patch("/{user_id}", response_model=UserRead)
def update_user(
    user_id: UUID,
    payload: UserUpdate,
    service: AuthServiceDep,
    current_user: CurrentUser,
) -> UserRead:
    """Actualiza un usuario (solo ADMIN)."""
    user = service.update_user(
        user_id=user_id,
        email=payload.email,
        full_name=payload.full_name,
        role=payload.role,
        is_active=payload.is_active,
    )
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado",
        )
    return UserRead.model_validate(user)
