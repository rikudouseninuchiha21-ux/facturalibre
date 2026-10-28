"""Tests del rate limiting de login (Fase 39B)."""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from fastapi.testclient import TestClient

import app.api.v1.auth as auth_module
from app.core.rate_limiter import login_rate_limiter


def _login(client: TestClient, email: str) -> Any:
    return client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "wrong-password-123"},
    )


def test_login_blocked_after_max_attempts(anonymous_client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr(auth_module, "RATE_LIMIT_ENABLED", True)
    login_rate_limiter()._attempts.clear()
    email = f"ratelimit-{uuid4()}@example.com"

    for _ in range(5):
        assert _login(anonymous_client, email).status_code == 401

    sixth = _login(anonymous_client, email)
    assert sixth.status_code == 429
    assert "Demasiados intentos" in sixth.json()["detail"]
    assert int(sixth.headers["Retry-After"]) >= 1
    login_rate_limiter()._attempts.clear()


def test_rate_limiter_is_per_email_and_ip(anonymous_client: TestClient, monkeypatch) -> None:
    """El límite aplica por email y por IP: 4 intentos de un email no
    bloquean a otro, pero la IP compartida sí se agota (5/min)."""
    monkeypatch.setattr(auth_module, "RATE_LIMIT_ENABLED", True)
    limiter = login_rate_limiter()
    limiter._attempts.clear()
    first = f"rl-{uuid4()}@example.com"
    second = f"rl-{uuid4()}@example.com"

    for _ in range(4):
        assert _login(anonymous_client, first).status_code == 401
    # Quinta ventana de la IP: email distinto sigue intentando sin bloqueo de email.
    assert _login(anonymous_client, second).status_code == 401
    # Sexto intento desde la misma IP dentro de la ventana → 429 por IP.
    assert _login(anonymous_client, first).status_code == 429
    limiter._attempts.clear()
