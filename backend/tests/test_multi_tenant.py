"""Pruebas de aislamiento entre empresas (multi-tenant)."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.application.auth.security import SESSION_COOKIE_NAME, hash_session_token
from app.domain.invoice_repository import InvoiceRepository
from app.domain.models.auth import AuthSession, User, UserRole
from app.domain.models.company import Company, UserCompany
from app.domain.models.contact import Contact
from app.domain.models.invoice import Invoice, LifecycleStatus, PaymentStatus


def _company(db: Session, name: str, tax_id: str) -> Company:
    company = Company(name=name, tax_id=tax_id)
    db.add(company)
    db.flush()
    return company


def _user(db: Session, email: str, role: UserRole = UserRole.ADMIN) -> User:
    user = User(
        email=email,
        hashed_password="dummy-hash",
        full_name=f"Usuario {email}",
        role=role,
        is_active=True,
    )
    db.add(user)
    db.flush()
    return user


def _membership(
    db: Session,
    user: User,
    company: Company,
    role: UserRole = UserRole.ADMIN,
) -> None:
    db.add(UserCompany(user_id=user.id, company_id=company.id, role=role))
    db.flush()


def _session(db: Session, user: User, company: Company) -> str:
    token = str(uuid4())
    db.add(
        AuthSession(
            user_id=user.id,
            token=hash_session_token(token),
            expires_at=datetime.now(UTC) + timedelta(hours=1),
            active_company_id=company.id,
        )
    )
    db.flush()
    return token


def _contact(db: Session, company: Company, name: str) -> Contact:
    contact = Contact(company_id=company.id, name=name)
    db.add(contact)
    db.flush()
    return contact


def _invoice(
    db: Session,
    company: Company,
    contact: Contact,
    number: str,
) -> Invoice:
    invoice = Invoice(
        company_id=company.id,
        number=number,
        contact_id=contact.id,
        issue_date=date(2026, 1, 1),
        due_date=date(2026, 1, 31),
        currency="COP",
        lifecycle_status=LifecycleStatus.ISSUED,
        payment_status=PaymentStatus.UNPAID,
        subtotal=Decimal("100.00"),
        tax_total=Decimal("0.00"),
        total=Decimal("100.00"),
        balance=Decimal("100.00"),
    )
    db.add(invoice)
    db.flush()
    return invoice


def _draft_invoice(db: Session, company: Company, contact: Contact) -> Invoice:
    invoice = Invoice(
        company_id=company.id,
        number=None,
        contact_id=contact.id,
        issue_date=date(2026, 2, 1),
        due_date=date(2026, 2, 28),
        currency="COP",
        lifecycle_status=LifecycleStatus.DRAFT,
        payment_status=PaymentStatus.UNPAID,
        subtotal=Decimal("50.00"),
        tax_total=Decimal("0.00"),
        total=Decimal("50.00"),
        balance=Decimal("50.00"),
    )
    db.add(invoice)
    db.flush()
    return invoice


def _client(db: Session, token: str) -> TestClient:
    from app.infrastructure.database import get_db
    from app.main import app

    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app, base_url="https://testserver")
    client.cookies.set(SESSION_COOKIE_NAME, token, path="/")
    return client


@pytest.fixture
def two_companies(db_session: Session) -> tuple[Company, Company]:
    return (
        _company(db_session, "Empresa Uno S.A.S.", "900000001-1"),
        _company(db_session, "Empresa Dos S.A.S.", "900000002-2"),
    )


def test_user_cannot_see_invoices_from_another_company(
    db_session: Session,
    two_companies: tuple[Company, Company],
) -> None:
    company_a, company_b = two_companies
    user = _user(db_session, "tenant-a@example.com")
    _membership(db_session, user, company_a, UserRole.ADMIN)
    token = _session(db_session, user, company_a)

    contact_a = _contact(db_session, company_a, "Cliente A")
    contact_b = _contact(db_session, company_b, "Cliente B")
    invoice_a = _invoice(db_session, company_a, contact_a, "FV-A-001")
    invoice_b = _invoice(db_session, company_b, contact_b, "FV-B-001")

    client = _client(db_session, token)
    try:
        response = client.get("/api/v1/invoices")
        assert response.status_code == 200, response.text
        numbers = {item["number"] for item in response.json()}
        assert "FV-A-001" in numbers
        assert "FV-B-001" not in numbers

        response = client.get(f"/api/v1/invoices/{invoice_a.id}")
        assert response.status_code == 200

        response = client.get(f"/api/v1/invoices/{invoice_b.id}")
        assert response.status_code == 404
    finally:
        client.close()
        _clear_overrides()


def test_switch_company_changes_visible_data(
    db_session: Session,
    two_companies: tuple[Company, Company],
) -> None:
    company_a, company_b = two_companies
    user = _user(db_session, "tenant-ab@example.com")
    _membership(db_session, user, company_a, UserRole.ADMIN)
    _membership(db_session, user, company_b, UserRole.ACCOUNTANT)
    token = _session(db_session, user, company_a)

    contact_a = _contact(db_session, company_a, "Cliente A")
    contact_b = _contact(db_session, company_b, "Cliente B")
    invoice_a = _invoice(db_session, company_a, contact_a, "FV-A-002")
    _invoice(db_session, company_b, contact_b, "FV-B-002")

    client = _client(db_session, token)
    try:
        assert [i["number"] for i in client.get("/api/v1/invoices").json()] == ["FV-A-002"]

        response = client.post(f"/api/v1/auth/switch-company/{company_b.id}")
        assert response.status_code == 200, response.text
        assert response.json()["active_company_id"] == str(company_b.id)
        assert response.json()["role"] == "ACCOUNTANT"

        assert [i["number"] for i in client.get("/api/v1/invoices").json()] == ["FV-B-002"]

        # Un id de la empresa anterior sigue siendo invisible tras el cambio.
        assert client.get(f"/api/v1/invoices/{invoice_a.id}").status_code == 404

        me = client.get("/api/v1/auth/me")
        assert me.status_code == 200
        assert me.json()["active_company_id"] == str(company_b.id)
        assert me.json()["role"] == "ACCOUNTANT"
    finally:
        client.close()
        _clear_overrides()


def test_switch_to_company_without_access_returns_403(
    db_session: Session,
    two_companies: tuple[Company, Company],
) -> None:
    company_a, company_b = two_companies
    user = _user(db_session, "tenant-forbidden@example.com")
    _membership(db_session, user, company_a, UserRole.ADMIN)
    token = _session(db_session, user, company_a)

    client = _client(db_session, token)
    try:
        response = client.post(f"/api/v1/auth/switch-company/{company_b.id}")
        assert response.status_code == 403
        assert response.json()["detail"] == "Sin acceso a la empresa solicitada"
    finally:
        client.close()
        _clear_overrides()


def test_company_admin_role_is_tenant_specific(
    db_session: Session,
    two_companies: tuple[Company, Company],
) -> None:
    company_a, company_b = two_companies
    user = _user(db_session, "tenant-role@example.com")
    _membership(db_session, user, company_a, UserRole.ADMIN)
    _membership(db_session, user, company_b, UserRole.ACCOUNTANT)
    token = _session(db_session, user, company_a)

    client = _client(db_session, token)
    try:
        # ADMIN en A puede crear empresas.
        response = client.post(
            "/api/v1/companies",
            json={"name": "Empresa Tres S.A.S.", "tax_id": "900000003-3"},
        )
        assert response.status_code == 201, response.text

        # ACCOUNTANT en B no puede crear empresas ni asignar usuarios.
        response = client.post(f"/api/v1/auth/switch-company/{company_b.id}")
        assert response.status_code == 200
        response = client.post(
            "/api/v1/companies",
            json={"name": "Empresa Cuatro S.A.S.", "tax_id": "900000004-4"},
        )
        assert response.status_code == 403
        response = client.get(f"/api/v1/companies/{company_b.id}/users")
        assert response.status_code == 403
    finally:
        client.close()
        _clear_overrides()


def test_numbering_sequences_are_independent_per_company(
    db_session: Session,
    two_companies: tuple[Company, Company],
) -> None:
    company_a, company_b = two_companies
    contact_a = _contact(db_session, company_a, "Cliente A")
    contact_b = _contact(db_session, company_b, "Cliente B")
    invoice_a = _draft_invoice(db_session, company_a, contact_a)
    invoice_b = _draft_invoice(db_session, company_b, contact_b)

    db_session.info["company_id"] = company_a.id
    issued_a = InvoiceRepository(db_session).issue(invoice_a.id)
    assert issued_a.number == "FV00000001"

    db_session.info["company_id"] = company_b.id
    issued_b = InvoiceRepository(db_session).issue(invoice_b.id)
    assert issued_b.number == "FV00000001"


def test_legacy_rows_have_a_default_company(db_session: Session) -> None:
    """Todas las tablas de negocio quedaron con company_id no nulo."""
    rows = db_session.execute(
        text(
            "SELECT table_name FROM information_schema.columns "
            "WHERE table_schema = 'public' AND column_name = 'company_id'"
        )
    ).all()
    tables = {row[0] for row in rows}
    assert "invoices" in tables
    assert "contacts" in tables
    assert "company_settings" in tables
    assert "accounting_entries" in tables

    for table in tables:
        missing = db_session.scalar(text(f"SELECT count(*) FROM {table} WHERE company_id IS NULL"))
        assert missing == 0, f"{table} tiene filas sin empresa"

    default_company = db_session.scalar(
        select(Company).order_by(Company.created_at, Company.id).limit(1)
    )
    assert default_company is not None
    settings_company = db_session.scalar(
        text("SELECT company_id FROM company_settings ORDER BY created_at, id LIMIT 1")
    )
    assert settings_company == default_company.id


def _clear_overrides() -> None:
    from app.main import app

    app.dependency_overrides.clear()
