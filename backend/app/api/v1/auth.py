"""Registro, login, logout y consulta del usuario autenticado."""

from __future__ import annotations

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
from app.domain.exceptions import (
    EmailAlreadyRegisteredError,
    InvalidCredentialsError,
    RegistrationClosedError,
)
from app.infrastructure.database import get_db

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
    db: DbSession,
) -> UserRead:
    """Valida credenciales y entrega una cookie de sesión HTTP-only."""
    try:
        user, token, expires_at = AuthService(db).login(payload)
    except InvalidCredentialsError as exc:
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
        samesite="lax",
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
        samesite="lax",
    )
    return response


@router.get("/me", response_model=UserRead)
def me(user: CurrentUser) -> UserRead:
    """Devuelve el usuario asociado a la sesión vigente."""
    return UserRead.model_validate(user)
