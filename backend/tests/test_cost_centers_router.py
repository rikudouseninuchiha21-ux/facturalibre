"""Tests del CRUD de centros de costo y sus permisos por rol."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.application.auth.security import hash_session_token
from app.domain.models.auth import AuthSession, User, UserRole


def _make_client_with_role(
    db_session: Session,
    role: UserRole,
) -> TestClient:
    """Crea un cliente autenticado con el rol indicado."""
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
    return client


def _payload() -> dict[str, Any]:
    return {"code": f"CC-{uuid4().hex[:8].upper()}", "name": "Ventas"}


def test_create_and_get_cost_center(client: TestClient) -> None:
    created = client.post("/api/v1/cost-centers", json=_payload())
    assert created.status_code == 201, created.text
    center = created.json()
    assert center["is_active"] is True
    assert center["code"].startswith("CC-")

    fetched = client.get(f"/api/v1/cost-centers/{center['id']}")
    assert fetched.status_code == 200, fetched.text
    assert fetched.json()["id"] == center["id"]


def test_duplicate_code_returns_conflict(client: TestClient) -> None:
    payload = _payload()
    first = client.post("/api/v1/cost-centers", json=payload)
    assert first.status_code == 201, first.text

    repeated = client.post("/api/v1/cost-centers", json=payload)
    assert repeated.status_code == 409, repeated.text
    assert "código" in repeated.json()["detail"]


def test_list_only_active_by_default(client: TestClient) -> None:
    active = client.post("/api/v1/cost-centers", json=_payload()).json()
    inactive_payload = _payload()
    inactive_payload["name"] = "Desactivado"
    inactive = client.post("/api/v1/cost-centers", json=inactive_payload).json()

    patched = client.patch(
        f"/api/v1/cost-centers/{inactive['id']}",
        json={"is_active": False},
    )
    assert patched.status_code == 200, patched.text
    assert patched.json()["is_active"] is False

    listed = client.get("/api/v1/cost-centers")
    assert listed.status_code == 200, listed.text
    codes = {center["code"] for center in listed.json()}
    assert active["code"] in codes
    assert inactive["code"] not in codes

    listed_all = client.get("/api/v1/cost-centers?include_inactive=true")
    codes_all = {center["code"] for center in listed_all.json()}
    assert inactive["code"] in codes_all


def test_update_cost_center(client: TestClient) -> None:
    center = client.post("/api/v1/cost-centers", json=_payload()).json()

    updated = client.patch(
        f"/api/v1/cost-centers/{center['id']}",
        json={"name": "Área comercial", "description": "Ventas nacionales"},
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["name"] == "Área comercial"
    assert updated.json()["description"] == "Ventas nacionales"


def test_delete_unreferenced_center_is_hard(client: TestClient) -> None:
    center = client.post("/api/v1/cost-centers", json=_payload()).json()

    deleted = client.delete(f"/api/v1/cost-centers/{center['id']}")
    assert deleted.status_code == 204, deleted.text

    fetched = client.get(f"/api/v1/cost-centers/{center['id']}")
    assert fetched.status_code == 404, fetched.text


def test_delete_referenced_center_deactivates(client: TestClient) -> None:
    center = client.post("/api/v1/cost-centers", json=_payload()).json()

    budget = client.post(
        "/api/v1/budgets",
        json={
            "cost_center_id": center["id"],
            "period_year": 2026,
            "period_month": 7,
        },
    )
    assert budget.status_code == 201, budget.text

    deleted = client.delete(f"/api/v1/cost-centers/{center['id']}")
    assert deleted.status_code == 204, deleted.text

    fetched = client.get(f"/api/v1/cost-centers/{center['id']}")
    assert fetched.status_code == 200, fetched.text
    assert fetched.json()["is_active"] is False


def test_cost_center_roles(db_session: Session, client: TestClient) -> None:
    accountant = _make_client_with_role(db_session, UserRole.ACCOUNTANT)
    created = accountant.post("/api/v1/cost-centers", json=_payload())
    assert created.status_code == 201, created.text

    cashier = _make_client_with_role(db_session, UserRole.CASHIER)
    assert cashier.get("/api/v1/cost-centers").status_code == 200
    assert cashier.post("/api/v1/cost-centers", json=_payload()).status_code == 403
    assert cashier.delete("/api/v1/cost-centers/{uuid4()}").status_code == 403

    center = created.json()
    assert accountant.delete(f"/api/v1/cost-centers/{center['id']}").status_code == 403

    admin_client = _make_client_with_role(db_session, UserRole.ADMIN)
    assert admin_client.delete(f"/api/v1/cost-centers/{center['id']}").status_code == 204


def test_cost_center_requires_authentication(
    anonymous_client: TestClient,
) -> None:
    assert anonymous_client.get("/api/v1/cost-centers").status_code == 401
    assert anonymous_client.post("/api/v1/cost-centers", json=_payload()).status_code == 401
