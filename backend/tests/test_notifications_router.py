"""Tests del router de notificaciones: aislamiento por usuario y marcado."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.application.auth.security import hash_session_token
from app.application.notification_service import NotificationService
from app.domain.models.auth import AuthSession, User, UserRole
from app.domain.models.notification import NotificationSeverity


def _make_client_and_user(
    db_session: Session,
    role: UserRole,
) -> tuple[TestClient, User]:
    from app.infrastructure.database import get_db
    from app.main import app

    user = User(
        email=f"{role.value.lower()}-{uuid4()}@example.com",
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

    def override_get_db() -> Any:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app, base_url="https://testserver")
    client.cookies.set("facturalibre_session", token, path="/")
    return client, user


def _notify(db_session: Session, user_id: Any, title: str) -> Any:
    return NotificationService(db_session).create(
        user_id=user_id,
        category="BUDGET_ALERT",
        severity=NotificationSeverity.WARNING,
        title=title,
        link="/budgets/abc",
    )


def test_notifications_require_authentication(anonymous_client: TestClient) -> None:
    assert anonymous_client.get("/api/v1/notifications").status_code == 401
    assert anonymous_client.get("/api/v1/notifications/unread-count").status_code == 401
    assert anonymous_client.post("/api/v1/notifications/mark-all-read").status_code == 401


def test_user_isolation_in_list_and_unread_count(
    db_session: Session,
    anonymous_client: TestClient,
) -> None:
    admin_client, admin_user = _make_client_and_user(db_session, UserRole.ADMIN)
    accountant_client, accountant_user = _make_client_and_user(db_session, UserRole.ACCOUNTANT)

    _notify(db_session, admin_user.id, "Notificación del admin")
    _notify(db_session, admin_user.id, "Otra del admin")
    _notify(db_session, accountant_user.id, "Notificación del contador")

    admin_list = admin_client.get("/api/v1/notifications")
    assert admin_list.status_code == 200, admin_list.text
    titles = {item["title"] for item in admin_list.json()}
    assert titles == {"Notificación del admin", "Otra del admin"}
    assert "Notificación del contador" not in titles

    admin_count = admin_client.get("/api/v1/notifications/unread-count")
    assert admin_count.json() == {"count": 2}

    accountant_list = accountant_client.get("/api/v1/notifications")
    assert {item["title"] for item in accountant_list.json()} == {"Notificación del contador"}


def test_mark_read_isolated_by_owner(db_session: Session) -> None:
    admin_client, admin_user = _make_client_and_user(db_session, UserRole.ADMIN)
    accountant_client, _ = _make_client_and_user(db_session, UserRole.ACCOUNTANT)

    notification = _notify(db_session, admin_user.id, "Solo del admin")

    # El contador no puede marcar la notificación del admin: 404 y sin cambio.
    foreign = accountant_client.post(f"/api/v1/notifications/{notification.id}/mark-read")
    assert foreign.status_code == 404, foreign.text

    owner = admin_client.post(f"/api/v1/notifications/{notification.id}/mark-read")
    assert owner.status_code == 204, owner.text

    repeated = admin_client.post(f"/api/v1/notifications/{notification.id}/mark-read")
    assert repeated.status_code == 404, repeated.text

    after = admin_client.get("/api/v1/notifications")
    assert after.json()[0]["read_at"] is not None
    assert admin_client.get("/api/v1/notifications/unread-count").json() == {"count": 0}


def test_mark_all_read_returns_marked_count(db_session: Session) -> None:
    admin_client, admin_user = _make_client_and_user(db_session, UserRole.ADMIN)
    for index in range(3):
        _notify(db_session, admin_user.id, f"Notificación {index}")

    response = admin_client.post("/api/v1/notifications/mark-all-read")
    assert response.status_code == 200, response.text
    assert response.json() == {"marked": 3}

    assert admin_client.get("/api/v1/notifications/unread-count").json() == {"count": 0}
    assert admin_client.get("/api/v1/notifications").json()[0]["read_at"] is not None


def test_list_respects_unread_only_and_pagination(db_session: Session) -> None:
    admin_client, admin_user = _make_client_and_user(db_session, UserRole.ADMIN)
    for index in range(4):
        notification = _notify(db_session, admin_user.id, f"Notificación {index}")
        if index < 2:
            admin_client.post(f"/api/v1/notifications/{notification.id}/mark-read")

    unread = admin_client.get("/api/v1/notifications?unread_only=true")
    titles = [item["title"] for item in unread.json()]
    assert set(titles) == {"Notificación 3", "Notificación 2"}

    page = admin_client.get("/api/v1/notifications?limit=2&offset=0")
    assert len(page.json()) == 2
