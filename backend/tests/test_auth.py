"""Tests de registro, login, logout y protección de endpoints."""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.application.auth.security import SESSION_COOKIE_NAME, hash_session_token
from app.domain.models.auth import AuthSession, User

REGISTER_PAYLOAD = {
    "email": "admin@example.com",
    "password": "contraseña-segura-123",
    "full_name": "Administrador Inicial",
}

PROTECTED_ENDPOINTS = (
    "/api/v1/contacts",
    "/api/v1/items",
    "/api/v1/taxes",
    "/api/v1/invoices",
    "/api/v1/accounting/accounts",
    "/api/v1/warehouses",
    "/api/v1/inventory/balances",
    "/api/v1/employees",
    "/api/v1/payroll/periods",
)


def _register(
    client: TestClient,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    response = client.post("/api/v1/auth/register", json=payload or REGISTER_PAYLOAD)
    assert response.status_code == 201, response.text
    return response.json()


def _login(client: TestClient) -> Any:
    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": REGISTER_PAYLOAD["email"],
            "password": REGISTER_PAYLOAD["password"],
        },
    )
    assert response.status_code == 200, response.text
    return response


def test_register_success_and_duplicate_email(
    anonymous_client: TestClient,
    db_session: Session,
) -> None:
    user = _register(
        anonymous_client,
        {
            **REGISTER_PAYLOAD,
            "email": "Admin@Example.com",
        },
    )

    assert user["email"] == "admin@example.com"
    assert user["full_name"] == "Administrador Inicial"
    assert user["is_active"] is True
    assert "hashed_password" not in user

    persisted = db_session.scalar(select(User).where(User.email == "admin@example.com"))
    assert persisted is not None
    assert persisted.hashed_password != REGISTER_PAYLOAD["password"]
    assert persisted.hashed_password.startswith("$2b$")

    duplicate = anonymous_client.post(
        "/api/v1/auth/register",
        json={
            **REGISTER_PAYLOAD,
            "email": "ADMIN@example.com",
        },
    )
    assert duplicate.status_code == 409
    assert duplicate.json() == {"detail": "El email ya está registrado"}


def test_register_is_closed_after_first_user(anonymous_client: TestClient) -> None:
    _register(anonymous_client)

    response = anonymous_client.post(
        "/api/v1/auth/register",
        json={
            "email": "segundo@example.com",
            "password": "otra-contraseña-123",
            "full_name": "Segundo Usuario",
        },
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "El registro inicial ya fue completado"}


def test_login_sets_secure_http_only_cookie(
    anonymous_client: TestClient,
    db_session: Session,
) -> None:
    _register(anonymous_client)

    response = _login(anonymous_client)
    set_cookie = response.headers["set-cookie"].lower()

    assert "httponly" in set_cookie
    assert "secure" in set_cookie
    assert "samesite=lax" in set_cookie
    assert "max-age=86400" in set_cookie

    raw_token = anonymous_client.cookies.get(SESSION_COOKIE_NAME)
    assert raw_token is not None

    session = db_session.scalar(
        select(AuthSession).where(AuthSession.token == hash_session_token(raw_token))
    )
    assert session is not None
    assert session.token != raw_token

    me = anonymous_client.get("/api/v1/auth/me")
    assert me.status_code == 200, me.text
    assert me.json()["email"] == "admin@example.com"
    assert me.json()["full_name"] == "Administrador Inicial"


@pytest.mark.parametrize(
    "credentials",
    (
        {"email": "admin@example.com", "password": "contraseña-incorrecta"},
        {"email": "no-existe@example.com", "password": "contraseña-segura-123"},
    ),
)
def test_login_with_invalid_credentials_returns_401(
    anonymous_client: TestClient,
    credentials: dict[str, str],
) -> None:
    _register(anonymous_client)

    response = anonymous_client.post("/api/v1/auth/login", json=credentials)

    assert response.status_code == 401
    assert response.json() == {"detail": "Email o contraseña incorrectos"}


@pytest.mark.parametrize("path", PROTECTED_ENDPOINTS)
def test_protected_endpoints_require_session(
    anonymous_client: TestClient,
    path: str,
) -> None:
    response = anonymous_client.get(path)

    assert response.status_code == 401
    assert response.json() == {"detail": "Sesión no válida o expirada"}


@pytest.mark.parametrize("path", PROTECTED_ENDPOINTS)
def test_protected_endpoints_accept_valid_session(client: TestClient, path: str) -> None:
    response = client.get(path)

    assert response.status_code == 200, response.text


def test_logout_revokes_session_and_clears_cookie(
    anonymous_client: TestClient,
    db_session: Session,
) -> None:
    _register(anonymous_client)
    _login(anonymous_client)
    raw_token = anonymous_client.cookies.get(SESSION_COOKIE_NAME)
    assert raw_token is not None

    logout = anonymous_client.post("/api/v1/auth/logout")
    assert logout.status_code == 204
    assert "max-age=0" in logout.headers["set-cookie"].lower()

    count = db_session.scalar(select(func.count()).select_from(AuthSession))
    assert count == 0

    # Aunque se reinyecte el token revocado, la sesión ya no existe en la BD.
    anonymous_client.cookies.set(
        SESSION_COOKIE_NAME,
        raw_token,
        path="/",
    )
    me = anonymous_client.get("/api/v1/auth/me")
    assert me.status_code == 401
