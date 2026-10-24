"""Tests de control de acceso basado en roles (RBAC).

Verifica que los usuarios con diferentes roles solo puedan acceder a los
endpoints autorizados según su rol.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from fastapi.testclient import TestClient

from app.application.auth.security import hash_session_token
from app.domain.models.auth import AuthSession, User, UserRole


def _make_client_with_user(db_session, role: UserRole, email: str) -> TestClient:
    """Crea un TestClient autenticado como el usuario dado con el rol indicado."""
    from app.infrastructure.database import get_db
    from app.main import app

    user = User(
        email=email,
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

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app, base_url="https://testserver")
    client.cookies.set(
        "facturalibre_session",
        token,
        path="/",
    )
    return client


def test_cashier_cannot_access_payroll_periods(db_session) -> None:
    """Un cajero no puede acceder a /api/v1/payroll/periods (debe devolver 403)."""
    client = _make_client_with_user(db_session, UserRole.CASHIER, "cajero@test.com")

    response = client.get("/api/v1/payroll/periods")
    assert response.status_code == 403, response.text


def test_cashier_can_access_pos_search(db_session) -> None:
    """Un cajero puede acceder a /api/v1/pos/search (debe devolver 200)."""
    client = _make_client_with_user(db_session, UserRole.CASHIER, "cajero@test.com")

    response = client.get("/api/v1/pos/search?q=test")
    assert response.status_code == 200, response.text


def test_accountant_can_access_purchases(db_session) -> None:
    """Un contador puede acceder a /api/v1/purchases (debe devolver 200)."""
    client = _make_client_with_user(db_session, UserRole.ACCOUNTANT, "contador@test.com")

    response = client.get("/api/v1/purchases")
    assert response.status_code == 200, response.text


def test_accountant_cannot_access_payroll_periods(db_session) -> None:
    """Un contador no puede acceder a /api/v1/payroll/periods (debe devolver 403)."""
    client = _make_client_with_user(db_session, UserRole.ACCOUNTANT, "contador2@test.com")

    response = client.get("/api/v1/payroll/periods")
    assert response.status_code == 403, response.text


def test_admin_can_access_everything(db_session) -> None:
    """Un administrador puede acceder a payroll, pos y reports."""
    client = _make_client_with_user(db_session, UserRole.ADMIN, "admin@test.com")

    assert client.get("/api/v1/payroll/periods").status_code == 200
    assert client.get("/api/v1/pos/search?q=test").status_code == 200
    assert client.get("/api/v1/reports/income-statement").status_code == 200


def test_unauthenticated_cannot_access_protected_endpoints(
    anonymous_client: TestClient,
) -> None:
    """Sin cookie de sesión, los endpoints protegidos devuelven 401."""
    assert anonymous_client.get("/api/v1/payroll/periods").status_code == 401
    assert anonymous_client.get("/api/v1/pos/search?q=test").status_code == 401
    assert anonymous_client.get("/api/v1/reports/income-statement").status_code == 401
