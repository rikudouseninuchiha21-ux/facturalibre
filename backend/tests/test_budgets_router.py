"""Tests del CRUD de presupuestos, sus líneas y su ciclo de vida."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.application.auth.security import hash_session_token
from app.domain.models.auth import AuthSession, User, UserRole


def _make_client_with_role(db_session: Session, role: UserRole) -> TestClient:
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


def _create_cost_center(client: TestClient) -> dict[str, Any]:
    response = client.post(
        "/api/v1/cost-centers",
        json={"code": f"CC-{uuid4().hex[:8].upper()}", "name": "Presupuesto"},
    )
    assert response.status_code == 201, response.text
    return response.json()


def _create_budget(
    client: TestClient,
    cost_center_id: str | UUID,
    *,
    year: int = 2026,
    month: int = 8,
) -> dict[str, Any]:
    response = client.post(
        "/api/v1/budgets",
        json={
            "cost_center_id": str(cost_center_id),
            "period_year": year,
            "period_month": month,
            "name": "Presupuesto de prueba",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def _add_line(
    client: TestClient,
    budget_id: str,
    account_code: str = "5199",
    amount: str = "1000.00",
) -> dict[str, Any]:
    response = client.post(
        f"/api/v1/budgets/{budget_id}/lines",
        json={"account_code": account_code, "amount": amount},
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_budget_lifecycle(client: TestClient) -> None:
    center = _create_cost_center(client)
    budget = _create_budget(client, center["id"])

    assert budget["status"] == "DRAFT"
    assert budget["lines"] == []
    assert budget["cost_center"]["id"] == center["id"]
    assert budget["total"] == "0.00"

    line = _add_line(client, budget["id"], account_code="5199", amount="1000.00")
    assert line["account_code"] == "5199"
    assert line["account_name"] == "Gastos diversos"
    assert line["amount"] == "1000.00"

    updated_line = client.patch(
        f"/api/v1/budgets/{budget['id']}/lines/{line['id']}",
        json={"amount": "1500.00"},
    )
    assert updated_line.status_code == 200, updated_line.text
    assert updated_line.json()["amount"] == "1500.00"

    patched = client.patch(
        f"/api/v1/budgets/{budget['id']}",
        json={"notes": "Revisión de gerencia"},
    )
    assert patched.status_code == 200, patched.text
    assert patched.json()["notes"] == "Revisión de gerencia"
    assert patched.json()["total"] == "1500.00"

    fetched = client.get(f"/api/v1/budgets/{budget['id']}")
    assert fetched.status_code == 200, fetched.text
    assert len(fetched.json()["lines"]) == 1


def test_budget_unique_per_center_and_period(client: TestClient) -> None:
    center = _create_cost_center(client)
    _create_budget(client, center["id"], year=2026, month=8)

    duplicate = client.post(
        "/api/v1/budgets",
        json={
            "cost_center_id": center["id"],
            "period_year": 2026,
            "period_month": 8,
        },
    )
    assert duplicate.status_code == 422, duplicate.text
    assert "ya tiene un presupuesto" in duplicate.json()["detail"]


def test_budget_line_validations(client: TestClient) -> None:
    center = _create_cost_center(client)
    budget = _create_budget(client, center["id"])
    _add_line(client, budget["id"], account_code="5199")

    duplicate = client.post(
        f"/api/v1/budgets/{budget['id']}/lines",
        json={"account_code": "5199", "amount": "5.00"},
    )
    assert duplicate.status_code == 422, duplicate.text

    missing_account = client.post(
        f"/api/v1/budgets/{budget['id']}/lines",
        json={"account_code": "999999", "amount": "5.00"},
    )
    assert missing_account.status_code == 422, missing_account.text

    negative = client.post(
        f"/api/v1/budgets/{budget['id']}/lines",
        json={"account_code": "5160", "amount": "-1.00"},
    )
    assert negative.status_code == 422, negative.text

    # Quitar una línea existente en DRAFT funciona; una inexistente da 404.
    lines = client.get(f"/api/v1/budgets/{budget['id']}").json()["lines"]
    assert len(lines) == 1
    removed = client.delete(f"/api/v1/budgets/{budget['id']}/lines/{lines[0]['id']}")
    assert removed.status_code == 204, removed.text
    assert client.get(f"/api/v1/budgets/{budget['id']}").json()["lines"] == []

    missing = client.delete(f"/api/v1/budgets/{budget['id']}/lines/{uuid4()}")
    assert missing.status_code == 404, missing.text


def test_approve_requires_lines_and_positive_total(client: TestClient) -> None:
    center = _create_cost_center(client)
    empty = _create_budget(client, center["id"])

    rejected = client.post(f"/api/v1/budgets/{empty['id']}/approve")
    assert rejected.status_code == 422, rejected.text
    assert "al menos una línea" in rejected.json()["detail"]

    zero = _create_budget(client, center["id"], month=9)
    _add_line(client, zero["id"], account_code="5199", amount="0.00")
    zero_rejected = client.post(f"/api/v1/budgets/{zero['id']}/approve")
    assert zero_rejected.status_code == 422, zero_rejected.text
    assert "mayor que cero" in zero_rejected.json()["detail"]


def test_budget_status_transitions_block_edition(client: TestClient) -> None:
    center = _create_cost_center(client)
    budget = _create_budget(client, center["id"])
    line = _add_line(client, budget["id"])

    approved = client.post(f"/api/v1/budgets/{budget['id']}/approve")
    assert approved.status_code == 200, approved.text
    assert approved.json()["status"] == "APPROVED"

    assert client.patch(f"/api/v1/budgets/{budget['id']}", json={"name": "X"}).status_code == 409
    assert (
        client.post(
            f"/api/v1/budgets/{budget['id']}/lines",
            json={"account_code": "5160", "amount": "10.00"},
        ).status_code
        == 409
    )
    assert (
        client.patch(
            f"/api/v1/budgets/{budget['id']}/lines/{line['id']}",
            json={"amount": "1.00"},
        ).status_code
        == 409
    )
    assert client.delete(f"/api/v1/budgets/{budget['id']}/lines/{line['id']}").status_code == 409
    assert client.delete(f"/api/v1/budgets/{budget['id']}").status_code == 409
    assert client.post(f"/api/v1/budgets/{budget['id']}/approve").status_code == 409

    closed = client.post(f"/api/v1/budgets/{budget['id']}/close")
    assert closed.status_code == 200, closed.text
    assert closed.json()["status"] == "CLOSED"

    assert client.post(f"/api/v1/budgets/{budget['id']}/close").status_code == 409
    assert client.patch(f"/api/v1/budgets/{budget['id']}", json={"name": "Y"}).status_code == 409


def test_budget_close_requires_approved(client: TestClient) -> None:
    center = _create_cost_center(client)
    budget = _create_budget(client, center["id"])

    response = client.post(f"/api/v1/budgets/{budget['id']}/close")
    assert response.status_code == 409, response.text
    assert "aprobados" in response.json()["detail"]


def test_budget_list_filters(client: TestClient) -> None:
    center = _create_cost_center(client)
    other = _create_cost_center(client)
    _create_budget(client, center["id"], year=2026, month=3)
    _create_budget(client, other["id"], year=2026, month=3)

    by_month = client.get("/api/v1/budgets?period_year=2026&period_month=3")
    assert by_month.status_code == 200, by_month.text
    assert len(by_month.json()) == 2

    by_center = client.get(f"/api/v1/budgets?cost_center_id={center['id']}")
    assert len(by_center.json()) == 1
    assert by_center.json()[0]["cost_center"]["id"] == center["id"]

    draft_only = client.get("/api/v1/budgets?status=DRAFT&period_year=2026&period_month=3")
    assert len(draft_only.json()) == 2

    empty = client.get("/api/v1/budgets?period_year=2030&period_month=1")
    assert empty.json() == []


def test_budget_delete_only_draft_and_roles(
    client: TestClient,
    db_session: Session,
) -> None:
    center = _create_cost_center(client)
    budget = _create_budget(client, center["id"])

    accountant = _make_client_with_role(db_session, UserRole.ACCOUNTANT)
    assert accountant.delete(f"/api/v1/budgets/{budget['id']}").status_code == 403

    deleted = client.delete(f"/api/v1/budgets/{budget['id']}")
    assert deleted.status_code == 204, deleted.text

    missing = client.get(f"/api/v1/budgets/{budget['id']}")
    assert missing.status_code == 404, missing.text


def test_budget_missing_center_returns_404(client: TestClient) -> None:
    response = client.post(
        "/api/v1/budgets",
        json={
            "cost_center_id": str(uuid4()),
            "period_year": 2026,
            "period_month": 1,
        },
    )
    assert response.status_code == 404, response.text
