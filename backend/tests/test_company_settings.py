"""Tests del guardado de configuración de empresa con campos DIAN.

Blinda dos bugs históricos del endpoint PUT /settings/company:
1. El frontend hacía POST (405) — corregido con apiPut en el frontend.
2. El endpoint flush-eaba sin commit y ``get_db`` solo hace ``close()``:
   los cambios se perdían en producción. Ahora la escritura vive dentro
   de ``operation_transaction``.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.application.auth.security import SESSION_COOKIE_NAME, hash_session_token
from app.domain.models.auth import AuthSession, User, UserRole
from app.domain.models.company_setting import CompanySetting

DIAN_PAYLOAD: dict[str, Any] = {
    "name": "Nexus ERP S.A.S.",
    "tax_id": "900123456",
    "address": "Carrera 15 # 88 - 21",
    "phone": "+57 300 000 0000",
    "email": "facturacion@nexus.co",
    "dv": "8",
    "tax_regime": "RESPONSABLE_IVA",
    "person_type": "JURIDICA",
    "fiscal_responsibility": "O-13",
    "dian_municipality_code": "11001",
    "dian_department_code": "11",
    "dian_resolution_number": "18764000123456",
    "dian_resolution_prefix": "FE",
    "dian_resolution_range_from": 1,
    "dian_resolution_range_to": 1000,
    "dian_resolution_valid_from": "2026-01-01",
    "dian_resolution_valid_to": "2027-12-31",
    "dian_software_id": "NEXUS-ERP-38A",
    "dian_software_pin": "fc8eac422eba",
    "dian_environment": "HABILITACION",
}


def _ensure_settings_row(db_session: Session) -> CompanySetting:
    """Garantiza la fila single-row de company_settings.

    La migración 0012 la siembra en bases nuevas, pero las bases de test
    antiguas pueden no tenerla: el test no debe depender de ese estado
    inicial (misma lección de aislamiento que en test_dian_router).
    """
    company = db_session.scalar(select(CompanySetting))
    if company is None:
        company = CompanySetting(name="Mi Empresa S.A.S.")
        db_session.add(company)
        db_session.flush()
    return company


def _make_client_with_role(db_session: Session, role: UserRole) -> TestClient:
    from app.infrastructure.database import get_db
    from app.main import app

    user = User(
        email=f"{role.value.lower()}-settings-{uuid4()}@example.com",
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
    client.cookies.set(SESSION_COOKIE_NAME, token, path="/")
    return client


def _clear_overrides() -> None:
    from app.main import app

    app.dependency_overrides.clear()


def test_get_returns_company_settings(db_session: Session) -> None:
    _ensure_settings_row(db_session)
    admin = _make_client_with_role(db_session, UserRole.ADMIN)
    try:
        response = admin.get("/api/v1/settings/company")
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["name"]
        assert body["dian_environment"] == "HABILITACION"
    finally:
        _clear_overrides()


def test_put_persists_dian_fields(db_session: Session) -> None:
    _ensure_settings_row(db_session)
    admin = _make_client_with_role(db_session, UserRole.ADMIN)
    try:
        response = admin.put("/api/v1/settings/company", json=DIAN_PAYLOAD)
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["dv"] == "8"
        assert body["dian_resolution_number"] == "18764000123456"
        assert body["dian_resolution_range_to"] == 1000
        assert body["dian_software_pin"] == "fc8eac422eba"

        # Persistencia real: releer la fila desde la base tras el commit
        # de operation_transaction.
        db_session.expire_all()
        stored = db_session.scalar(select(CompanySetting))
        assert stored is not None
        assert stored.tax_id == "900123456"
        assert stored.dv == "8"
        assert stored.dian_resolution_prefix == "FE"
        assert stored.dian_resolution_valid_from is not None
        assert stored.dian_software_id == "NEXUS-ERP-38A"
        assert stored.dian_environment == "HABILITACION"
    finally:
        _clear_overrides()


def test_put_partial_update_keeps_dian_fields(db_session: Session) -> None:
    _ensure_settings_row(db_session)
    admin = _make_client_with_role(db_session, UserRole.ADMIN)
    try:
        first = admin.put("/api/v1/settings/company", json=DIAN_PAYLOAD)
        assert first.status_code == 200, first.text

        # PUT parcial: solo name. El resto de los campos DIAN no se toca.
        second = admin.put("/api/v1/settings/company", json={"name": "Otra Razón Social"})
        assert second.status_code == 200, second.text

        db_session.expire_all()
        stored = db_session.scalar(select(CompanySetting))
        assert stored is not None
        assert stored.name == "Otra Razón Social"
        assert stored.dv == "8"
        assert stored.dian_resolution_number == "18764000123456"
        assert stored.dian_software_pin == "fc8eac422eba"
    finally:
        _clear_overrides()


def test_put_requires_admin(db_session: Session) -> None:
    _ensure_settings_row(db_session)
    accountant = _make_client_with_role(db_session, UserRole.ACCOUNTANT)
    try:
        response = accountant.put("/api/v1/settings/company", json=DIAN_PAYLOAD)
        assert response.status_code == 403, response.text
    finally:
        _clear_overrides()
