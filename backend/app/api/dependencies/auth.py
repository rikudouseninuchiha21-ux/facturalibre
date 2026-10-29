"""Dependencias de FastAPI para sesión, empresa activa y roles por tenant."""

from __future__ import annotations

from collections.abc import Callable
from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.application.auth.security import SESSION_COOKIE_NAME
from app.application.auth.service import AuthService
from app.domain.models.auth import User, UserRole
from app.infrastructure.database import get_db
from app.infrastructure.tenancy import set_company_id

DbSession = Annotated[Session, Depends(get_db)]


def get_current_user(request: Request, db: DbSession) -> User:
    """Valida la cookie de sesión y resuelve la empresa activa del usuario."""
    token = request.cookies.get(SESSION_COOKIE_NAME)
    service = AuthService(db)
    context = service.get_session_by_token(token)

    if context is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sesión no válida o expirada",
            headers={"WWW-Authenticate": "Cookie"},
        )

    user, auth_session = context
    membership = service.resolve_membership(user, auth_session)
    set_company_id(db, membership.company.id)

    # Atributos de contexto: no son columnas, solo viven en esta petición.
    user.active_company_id = membership.company.id
    user.active_role = membership.role

    # La consulta de sesión abre una transacción. Se cierra antes de entrar al
    # endpoint para que `operation_transaction` sea el dueño de la transacción
    # de negocio y pueda confirmar sus cambios (no solo liberar un savepoint).
    db.commit()
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def get_current_company_id(current_user: CurrentUser) -> UUID:
    """Dependencia pública para obtener el tenant activo."""
    company_id = getattr(current_user, "active_company_id", None)
    if company_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="El usuario no tiene una empresa activa",
        )
    return company_id


CurrentCompanyId = Annotated[UUID, Depends(get_current_company_id)]


def get_current_user_optional(request: Request, db: DbSession) -> User | None:
    """Usuario autenticado o ``None``: para endpoints públicos que
    enriquecen el registro cuando hay sesión (p. ej. consentimientos)."""
    token = request.cookies.get(SESSION_COOKIE_NAME)
    if token is None:
        return None
    user = AuthService(db).get_user_by_token(token)
    db.commit()
    return user


def require_role(allowed_roles: list[UserRole]) -> Callable[[User], User]:
    """Devuelve una dependencia que verifica el rol en la empresa activa."""

    def role_checker(current_user: CurrentUser) -> User:
        active_role = getattr(current_user, "active_role", current_user.role)
        if active_role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tiene permisos para acceder a este recurso",
            )
        return current_user

    return role_checker
