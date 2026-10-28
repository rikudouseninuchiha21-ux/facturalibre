"""Registro, login, logout y consulta del usuario autenticado."""

from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from app.api.dependencies.auth import CurrentUser
from app.application.auth.schemas import LoginRequest, RegisterRequest, UserRead
from app.application.auth.security import (
    SESSION_COOKIE_NAME,
    SESSION_TTL_SECONDS,
)
from app.application.auth.service import AuthService
from app.core.rate_limiter import RATE_LIMIT_ENABLED, login_rate_limiter
from app.domain.exceptions import (
    EmailAlreadyRegisteredError,
    InvalidCredentialsError,
    RegistrationClosedError,
)
from app.infrastructure.database import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])

DbSession = Annotated[Session, Depends(get_db)]


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


@router.post("/login", response_model=UserRead)
def login(
    payload: LoginRequest,
    response: Response,
    request: Request,
    db: DbSession,
) -> UserRead:
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
        user, token, expires_at = AuthService(db).login(payload)
    except InvalidCredentialsError as exc:
        logger.warning("Login fallido desde %s para %s", client_ip, payload.email)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email o contraseña incorrectos",
            headers={"WWW-Authenticate": "Cookie"},
        ) from exc

    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=token,
        max_age=SESSION_TTL_SECONDS,
        expires=expires_at,
        path="/",
        secure=True,
        httponly=True,
        samesite="strict",
    )
    return UserRead.model_validate(user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(request: Request, db: DbSession) -> Response:
    """Revoca la sesión actual y elimina la cookie."""
    AuthService(db).logout(request.cookies.get(SESSION_COOKIE_NAME))

    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    response.delete_cookie(
        key=SESSION_COOKIE_NAME,
        path="/",
        secure=True,
        httponly=True,
        samesite="strict",
    )
    return response


@router.get("/me", response_model=UserRead)
def me(user: CurrentUser) -> UserRead:
    """Devuelve el usuario asociado a la sesión vigente."""
    return UserRead.model_validate(user)
