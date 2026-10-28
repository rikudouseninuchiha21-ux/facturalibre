"""Tests de hardening de sesiones: cookie segura y rotación en login."""

from __future__ import annotations

from app.application.auth.service import AuthService
from app.core.rate_limiter import login_rate_limiter


def test_login_cookie_is_http_only_strict(anonymous_client) -> None:
    """HttpOnly y SameSite=Strict siempre; Secure solo en producción.

    En la suite (ENVIRONMENT=test) la cookie no lleva Secure para que
    http://localhost funcione: ``session_cookie_secure`` lo decide por
    entorno y tiene su propio test.
    """
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
    assert "samesite=strict" in cookie
    assert "secure" not in cookie
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


def test_session_cookie_secure_depends_on_environment(monkeypatch) -> None:
    """El flag Secure de la cookie solo se exige en producción."""
    from app.application.auth import security

    class FakeSettings:
        def __init__(self, environment: str) -> None:
            self.environment = environment

    monkeypatch.setattr(security, "get_settings", lambda: FakeSettings("production"))
    assert security.session_cookie_secure() is True
    monkeypatch.setattr(security, "get_settings", lambda: FakeSettings("prod"))
    assert security.session_cookie_secure() is True
    monkeypatch.setattr(security, "get_settings", lambda: FakeSettings("development"))
    assert security.session_cookie_secure() is False
    monkeypatch.setattr(security, "get_settings", lambda: FakeSettings("test"))
    assert security.session_cookie_secure() is False
