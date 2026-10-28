"""Tests de hardening de sesiones: cookie segura y rotación en login."""

from __future__ import annotations

from app.application.auth.service import AuthService
from app.core.rate_limiter import login_rate_limiter


def test_login_cookie_is_http_only_secure_strict(anonymous_client) -> None:
    login_rate_limiter()._attempts.clear()
    anonymous_client.post(
        "/api/v1/auth/register",
        json={
            "email": "hardening@example.com",
            "password": "seguro-pero-recordable",
            "full_name": "Hardening",
        },
    )
    response = anonymous_client.post(
        "/api/v1/auth/login",
        json={"email": "hardening@example.com", "password": "seguro-pero-recordable"},
    )
    assert response.status_code == 200
    cookie = response.headers["set-cookie"].lower()
    assert "httponly" in cookie
    assert "secure" in cookie
    assert "samesite=strict" in cookie
    login_rate_limiter()._attempts.clear()


def test_login_invalidates_old_tokens(anonymous_client, db_session) -> None:
    login_rate_limiter()._attempts.clear()
    anonymous_client.post(
        "/api/v1/auth/register",
        json={
            "email": "rotate@example.com",
            "password": "seguro-pero-recordable",
            "full_name": "Rotación",
        },
    )
    first = anonymous_client.post(
        "/api/v1/auth/login",
        json={"email": "rotate@example.com", "password": "seguro-pero-recordable"},
    )
    first_token = first.headers["set-cookie"].split(";")[0].split("=", 1)[1]

    second = anonymous_client.post(
        "/api/v1/auth/login",
        json={"email": "rotate@example.com", "password": "seguro-pero-recordable"},
    )
    assert second.status_code == 200
    second_token = second.headers["set-cookie"].split(";")[0].split("=", 1)[1]

    assert first_token != second_token
    # La sesión anterior quedó revocada.
    resolved = AuthService(db_session).get_user_by_token(first_token)
    assert resolved is None
    assert AuthService(db_session).get_user_by_token(second_token) is not None
    login_rate_limiter()._attempts.clear()
