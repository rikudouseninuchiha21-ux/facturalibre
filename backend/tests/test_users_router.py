"""Smoke tests del router de usuarios.

El router existía pero nunca se registró en ``app.main``: la página /users
del frontend llamaba POST /api/v1/users y recibía 404. Estos tests fijan el
registro para que no vuelva a "desaparecer".
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.application.auth.security import SESSION_COOKIE_NAME, hash_session_token
from app.domain.models.auth import AuthSession, User, UserRole


def _make_client_with_role(
    db_session: Session,
    role: UserRole,
    *,
    anonymous: bool = False,
) -> TestClient:
    from app.infrastructure.database import get_db
    from app.main import app

    def override_get_db() -> Any:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app, base_url="https://testserver")

    if anonymous:
        return client

    user = User(
        email=f"{role.value.lower()}-users-{uuid4()}@example.com",
        hashed_password="dummy-hash",
        full_name=f"Usuario {role.value}",
        role=role,
        is_active=True,
    )
    db_session.add(user)
    db_session.flush()

    token = str(uuid4())
    db_session.add(
        AuthSession(
            user_id=user.id,
            token=hash_session_token(token),
            expires_at=datetime.now(UTC) + timedelta(hours=1),
        )
    )
    db_session.flush()

    client.cookies.set(SESSION_COOKIE_NAME, token, path="/")
    return client


def _clear_overrides() -> None:
    from app.main import app

    app.dependency_overrides.clear()


def test_users_require_authentication(db_session: Session) -> None:
    anonymous = _make_client_with_role(db_session, UserRole.ADMIN, anonymous=True)
    try:
        assert anonymous.get("/api/v1/users").status_code == 401
    finally:
        _clear_overrides()


def test_users_forbidden_for_non_admin(db_session: Session) -> None:
    accountant = _make_client_with_role(db_session, UserRole.ACCOUNTANT)
    try:
        assert accountant.get("/api/v1/users").status_code == 403
    finally:
        _clear_overrides()


def test_admin_creates_and_updates_user(db_session: Session) -> None:
    admin = _make_client_with_role(db_session, UserRole.ADMIN)
    try:
        created = admin.post(
            "/api/v1/users",
            json={
                "email": f"cajero-{uuid4()}@example.com",
                "password": "secreto-seguro-123",
                "full_name": "Cajero de Prueba",
                "role": "CASHIER",
            },
        )
        assert created.status_code == 201, created.text
        user_id = created.json()["id"]
        assert created.json()["role"] == "CASHIER"

        updated = admin.patch(
            f"/api/v1/users/{user_id}",
            json={"full_name": "Cajero Renombrado", "role": "ACCOUNTANT"},
        )
        assert updated.status_code == 200, updated.text
        assert updated.json()["role"] == "ACCOUNTANT"
        assert updated.json()["full_name"] == "Cajero Renombrado"

        listed = admin.get("/api/v1/users")
        assert listed.status_code == 200, listed.text
        assert user_id in {user["id"] for user in listed.json()}
    finally:
        _clear_overrides()
