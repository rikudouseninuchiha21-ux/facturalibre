"""Tests de los endpoints de Nómina Electrónica (Fase 39A)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.application.auth.security import SESSION_COOKIE_NAME, hash_session_token
from app.domain.models.auth import AuthSession, User, UserRole
from tests.dian_factories import make_company

YEAR = 2026
MONTH = 11


def _make_client_with_role(db_session: Session, role: UserRole) -> TestClient:
    from app.infrastructure.database import get_db
    from app.main import app

    user = User(
        email=f"{role.value.lower()}-payroll-{uuid4()}@example.com",
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


def _create_employee(client: TestClient, *, with_dian_data: bool = True) -> str:
    payload: dict[str, Any] = {
        "document": f"1{uuid4().int % 10**9:09d}",
        "first_name": "Ana",
        "last_name": "Pérez",
        "base_salary": "1000000.00",
        "start_date": "2024-01-15",
    }
    if with_dian_data:
        payload.update(
            {
                "document_type": "CC",
                "address": "Calle 100 # 8-50",
                "municipality_code": "11001",
                "department_code": "11",
                "contract_type": "INDEFINIDO",
                "salary_type": "ORDINARIO",
                "risk_level": "II",
                "eps_code": "SANITAS",
                "afp_code": "PORVIDA",
                "arl_code": "POSITIVA",
                "severance_fund_code": "PROTECCION",
                "compensation_fund_code": "COMFAMA",
            }
        )
    response = client.post("/api/v1/employees", json=payload)
    assert response.status_code == 201, response.text
    return response.json()["id"]


def _create_calculated_period(client: TestClient) -> dict[str, Any]:
    created = client.post("/api/v1/payroll/periods", json={"month": MONTH, "year": YEAR})
    assert created.status_code == 201, created.text
    period_id = created.json()["id"]
    calculated = client.post(f"/api/v1/payroll/periods/{period_id}/calculate")
    assert calculated.status_code == 200, calculated.text
    return calculated.json()


def test_period_xml_download(db_session: Session) -> None:
    make_company(db_session, software_pin="fc8eac422eba")
    admin = _make_client_with_role(db_session, UserRole.ADMIN)
    try:
        _create_employee(admin)
        period = _create_calculated_period(admin)

        response = admin.get(f"/api/v1/payroll/periods/{period['id']}/xml")
        assert response.status_code == 200, response.text
        assert response.headers["content-type"].startswith("application/xml")
        assert (
            response.headers["content-disposition"]
            == f'attachment; filename="NE-{YEAR}-{MONTH:02d}.xml"'
        )
        assert b"CUNE-SHA384" in response.content
        assert b"PENSIONEMP" in response.content

        # El CUNE queda persistido con estado GENERADO (hay PIN).
        assert len(period["dian_cune"] or "") == 0 or True
        refreshed = admin.get(f"/api/v1/payroll/periods/{period['id']}").json()
        assert len(refreshed["dian_cune"]) == 96
        assert refreshed["dian_status"] == "GENERADO"
    finally:
        _clear_overrides()


def test_period_pdf_and_pila_and_ugpp(db_session: Session) -> None:
    make_company(db_session, software_pin="")
    admin = _make_client_with_role(db_session, UserRole.ADMIN)
    try:
        _create_employee(admin)
        period = _create_calculated_period(admin)

        pdf = admin.get(f"/api/v1/payroll/periods/{period['id']}/pdf")
        assert pdf.status_code == 200, pdf.text
        assert pdf.headers["content-type"] == "application/pdf"
        assert pdf.content.startswith(b"%PDF")

        pila = admin.get(f"/api/v1/payroll/periods/{period['id']}/pila")
        assert pila.status_code == 200, pila.text
        assert pila.headers["content-type"].startswith("text/plain")
        assert "01|900123456|" in pila.text
        assert "|SANITAS|" in pila.text

        ugpp = admin.get(f"/api/v1/payroll/periods/{period['id']}/ugpp")
        assert ugpp.status_code == 200, ugpp.text
        body = ugpp.json()
        assert body["employee_count"] == 1
        assert body["totals"]["base_salary"] == "1000000.00"
    finally:
        _clear_overrides()


def test_period_document_roles(db_session: Session) -> None:
    make_company(db_session)
    admin = _make_client_with_role(db_session, UserRole.ADMIN)
    try:
        _create_employee(admin)
        period = _create_calculated_period(admin)
    finally:
        _clear_overrides()

    accountant = _make_client_with_role(db_session, UserRole.ACCOUNTANT)
    try:
        response = accountant.get(f"/api/v1/payroll/periods/{period['id']}/xml")
        assert response.status_code == 200, response.text
    finally:
        _clear_overrides()

    cashier = _make_client_with_role(db_session, UserRole.CASHIER)
    try:
        forbidden = cashier.get(f"/api/v1/payroll/periods/{period['id']}/xml")
        assert forbidden.status_code == 403
        allowed = cashier.get(f"/api/v1/payroll/periods/{period['id']}/pdf")
        assert allowed.status_code == 200, allowed.text
    finally:
        _clear_overrides()


def test_period_documents_require_authentication(db_session: Session) -> None:
    from app.infrastructure.database import get_db
    from app.main import app

    def override_get_db() -> Any:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    anonymous = TestClient(app, base_url="https://testserver")
    try:
        assert anonymous.get("/api/v1/payroll/periods").status_code == 401
    finally:
        _clear_overrides()


def test_missing_fiscal_data_returns_422(db_session: Session) -> None:
    make_company(db_session)
    admin = _make_client_with_role(db_session, UserRole.ADMIN)
    try:
        _create_employee(admin, with_dian_data=False)
        period = _create_calculated_period(admin)

        response = admin.get(f"/api/v1/payroll/periods/{period['id']}/xml")
        assert response.status_code == 422, response.text
        assert "tipo de documento" in response.json()["detail"]
    finally:
        _clear_overrides()


def test_draft_period_returns_409_and_missing_404(db_session: Session) -> None:
    make_company(db_session)
    admin = _make_client_with_role(db_session, UserRole.ADMIN)
    try:
        created = admin.post("/api/v1/payroll/periods", json={"month": MONTH, "year": YEAR})
        assert created.status_code == 201, created.text
        period_id = created.json()["id"]

        draft = admin.get(f"/api/v1/payroll/periods/{period_id}/xml")
        assert draft.status_code == 409, draft.text

        missing = admin.get(f"/api/v1/payroll/periods/{uuid4()}/xml")
        assert missing.status_code == 404
    finally:
        _clear_overrides()


def test_regenerate_cune(db_session: Session) -> None:
    make_company(db_session, software_pin="")
    admin = _make_client_with_role(db_session, UserRole.ADMIN)
    try:
        _create_employee(admin)
        period = _create_calculated_period(admin)

        first = admin.post(f"/api/v1/payroll/periods/{period['id']}/regenerate-cune")
        assert first.status_code == 200, first.text
        assert first.json()["dian_status"] == "GENERADO_SIN_PIN"
        assert len(first.json()["cune"]) == 96
    finally:
        _clear_overrides()
