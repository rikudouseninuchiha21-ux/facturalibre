"""Registro, login, logout y consulta del usuario autenticado."""

from __future__ import annotations

import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from app.api.dependencies.auth import CurrentUser
from app.application.auth.schemas import (
    LoginRequest,
    RegisterRequest,
    SessionUserRead,
    UserCompanyRead,
    UserRead,
)
from app.application.auth.security import (
    SESSION_COOKIE_NAME,
    SESSION_TTL_SECONDS,
    session_cookie_secure,
)
from app.application.auth.service import AuthService, LoginResult
from app.core.rate_limiter import RATE_LIMIT_ENABLED, login_rate_limiter
from app.domain.company_repository import CompanyRepository
from app.domain.exceptions import (
    EmailAlreadyRegisteredError,
    InvalidCredentialsError,
    RegistrationClosedError,
)
from app.domain.models.auth import User, UserRole
from app.infrastructure.database import get_db
from app.infrastructure.transactions import operation_transaction

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])

DbSession = Annotated[Session, Depends(get_db)]


def _session_user(
    db: Session,
    user: User,
    *,
    role: UserRole,
    active_company_id: UUID | None,
) -> SessionUserRead:
    """Construye la respuesta con empresa activa y membresías."""
    memberships = CompanyRepository(db).list_for_user(user.id)
    active = next(
        (item for item in memberships if item.company.id == active_company_id),
        None,
    )
    return SessionUserRead(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=role,
        is_active=user.is_active,
        created_at=user.created_at,
        active_company_id=active.company.id if active is not None else None,
        active_company_name=active.company.name if active is not None else None,
        companies=[
            UserCompanyRead(
                id=item.company.id,
                name=item.company.name,
                tax_id=item.company.tax_id,
                role=item.role,
            )
            for item in memberships
        ],
    )


@router.post(
    "/register",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
)
def register(payload: RegisterRequest, db: DbSession) -> UserRead:
    """Crea el primer usuario. El registro público se cierra después."""
    try:
        user = AuthService(db).register(payload)
    except EmailAlreadyRegisteredError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    except RegistrationClosedError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc

    return UserRead.model_validate(user)


@router.post("/login", response_model=SessionUserRead)
def login(
    payload: LoginRequest,
    response: Response,
    request: Request,
    db: DbSession,
) -> SessionUserRead:
    """Valida credenciales y entrega una cookie de sesión HTTP-only.

    Hardening (Fase 39B): rate limit por IP y email (5/min), rotación de
    sesiones al autenticar y log de auditoría de intentos fallidos.
    """
    client_ip = request.client.host if request.client else "unknown"
    limiter = login_rate_limiter()
    allowed_email, retry_email = limiter.check(f"email:{payload.email}")
    allowed_ip, retry_ip = limiter.check(f"ip:{client_ip}")
    if RATE_LIMIT_ENABLED and (not allowed_email or not allowed_ip):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Demasiados intentos de inicio de sesión; espera un momento",
            headers={"Retry-After": str(max(retry_email, retry_ip))},
        )

    try:
        result: LoginResult = AuthService(db).login(payload)
    except InvalidCredentialsError as exc:
        logger.warning("Login fallido desde %s para %s", client_ip, payload.email)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email o contraseña incorrectos",
            headers={"WWW-Authenticate": "Cookie"},
        ) from exc

    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=result.token,
        max_age=SESSION_TTL_SECONDS,
        expires=result.expires_at,
        path="/",
        secure=session_cookie_secure(),
        httponly=True,
        samesite="strict",
    )
    return _session_user(
        db,
        result.user,
        role=result.membership.role,
        active_company_id=result.membership.company.id,
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(request: Request, db: DbSession) -> Response:
    """Revoca la sesión actual y elimina la cookie."""
    AuthService(db).logout(request.cookies.get(SESSION_COOKIE_NAME))

    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    response.delete_cookie(
        key=SESSION_COOKIE_NAME,
        path="/",
        secure=session_cookie_secure(),
        httponly=True,
        samesite="strict",
    )
    return response


@router.get("/me", response_model=SessionUserRead)
def me(user: CurrentUser, db: DbSession) -> SessionUserRead:
    """Devuelve el usuario, su empresa activa y sus membresías."""
    return _session_user(
        db,
        user,
        role=getattr(user, "active_role", user.role),
        active_company_id=getattr(user, "active_company_id", None),
    )


@router.post("/switch-company/{company_id}", response_model=SessionUserRead)
def switch_company(
    company_id: UUID,
    request: Request,
    user: CurrentUser,
    db: DbSession,
) -> SessionUserRead:
    """Cambia la empresa activa de la sesión actual."""
    token = request.cookies.get(SESSION_COOKIE_NAME)
    context = AuthService(db).get_session_by_token(token)
    if context is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sesión no válida o expirada",
        )
    _, auth_session = context
    # Cierra la transacción de lectura para que operation_transaction sea el
    # dueño del commit (regla de transacciones del proyecto).
    db.commit()

    try:
        with operation_transaction(db):
            membership = AuthService(db).switch_company(user, auth_session, company_id)
    except PermissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc

    # Evita reutilizar instancias del tenant anterior desde el identity map.
    db.expire_all()

    return _session_user(
        db,
        user,
        role=membership.role,
        active_company_id=membership.company.id,
    )
