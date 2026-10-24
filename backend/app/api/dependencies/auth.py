"""Dependencias de FastAPI para resolver la sesión actual y el control de acceso por roles."""

from __future__ import annotations

from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.application.auth.security import SESSION_COOKIE_NAME
from app.application.auth.service import AuthService
from app.domain.models.auth import User, UserRole
from app.infrastructure.database import get_db

DbSession = Annotated[Session, Depends(get_db)]


def get_current_user(request: Request, db: DbSession) -> User:
    """Valida la cookie de sesión contra la tabla sessions."""
    token = request.cookies.get(SESSION_COOKIE_NAME)
    user = AuthService(db).get_user_by_token(token)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sesión no válida o expirada",
            headers={"WWW-Authenticate": "Cookie"},
        )

    # La consulta de sesión abre una transacción. Se cierra antes de entrar al
    # endpoint para que `operation_transaction` sea el dueño de la transacción
    # de negocio y pueda confirmar sus cambios (no solo liberar un savepoint).
    db.commit()
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_role(allowed_roles: list[UserRole]) -> Callable[[User], User]:
    """Devuelve una dependencia que verifica que el usuario tenga uno de los roles permitidos.

    Uso:
        router = APIRouter(dependencies=[Depends(require_role([UserRole.ADMIN]))])
    """

    def role_checker(current_user: CurrentUser) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tiene permisos para acceder a este recurso",
            )
        return current_user

    return role_checker
