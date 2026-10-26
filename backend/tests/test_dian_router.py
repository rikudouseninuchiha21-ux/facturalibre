"""Tests de los endpoints de documentos DIAN (XML/PDF/preview/CUFE)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

from fastapi.testclient import TestClient
from lxml import etree
from sqlalchemy.orm import Session

from app.application.auth.security import SESSION_COOKIE_NAME, hash_session_token
from app.domain.models.auth import AuthSession, User, UserRole
from app.domain.models.invoice import DianDocumentStatus, LifecycleStatus
from tests.dian_factories import make_full_package


def _make_client_with_role(db_session: Session, role: UserRole) -> TestClient:
    from app.infrastructure.database import get_db
    from app.main import app

    user = User(
        email=f"{role.value.lower()}-dian-{uuid4()}@example.com",
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


def _download(client: TestClient, invoice_id: str, extension: str) -> Any:
    return client.get(f"/api/v1/invoices/{invoice_id}/{extension}")


def test_xml_download_returns_attachment(db_session: Session) -> None:
    admin = _make_client_with_role(db_session, UserRole.ADMIN)
    try:
        invoice, _company, _contact, _taxes = make_full_package(db_session)
        response = _download(admin, str(invoice.id), "xml")
        assert response.status_code == 200, response.text
        assert response.headers["content-type"].startswith("application/xml")
        assert response.headers["content-disposition"] == (
            f'attachment; filename="FV-{invoice.number}.xml"'
        )
        assert response.content.startswith(b"<?xml")
        assert b"CUFE-SHA384" in response.content
    finally:
        _clear_overrides()


def test_pdf_download(db_session: Session) -> None:
    admin = _make_client_with_role(db_session, UserRole.ADMIN)
    try:
        invoice, _company, _contact, _taxes = make_full_package(db_session)
        response = _download(admin, str(invoice.id), "pdf")
        assert response.status_code == 200, response.text
        assert response.headers["content-type"] == "application/pdf"
        assert response.content.startswith(b"%PDF")
    finally:
        _clear_overrides()


def test_missing_invoice_returns_404(db_session: Session) -> None:
    admin = _make_client_with_role(db_session, UserRole.ADMIN)
    try:
        response = _download(admin, str(uuid4()), "xml")
        assert response.status_code == 404
    finally:
        _clear_overrides()


def test_draft_invoice_returns_409(db_session: Session) -> None:
    admin = _make_client_with_role(db_session, UserRole.ADMIN)
    try:
        invoice, _company, _contact, _taxes = make_full_package(db_session)
        invoice.lifecycle_status = LifecycleStatus.DRAFT
        db_session.flush()
        response = _download(admin, str(invoice.id), "xml")
        assert response.status_code == 409, response.text
    finally:
        _clear_overrides()


def test_incomplete_dian_data_returns_422(db_session: Session) -> None:
    admin = _make_client_with_role(db_session, UserRole.ADMIN)
    try:
        invoice, _company, _contact, _taxes = make_full_package(
            db_session, contact_with_dian_data=False
        )
        response = _download(admin, str(invoice.id), "xml")
        assert response.status_code == 422, response.text
        assert "contacto.dv" in response.json()["detail"]
    finally:
        _clear_overrides()


def test_cashier_can_download_xml(db_session: Session) -> None:
    cashier = _make_client_with_role(db_session, UserRole.CASHIER)
    try:
        invoice, _company, _contact, _taxes = make_full_package(db_session)
        response = _download(cashier, str(invoice.id), "xml")
        assert response.status_code == 200, response.text
    finally:
        _clear_overrides()


def test_dian_preview_admin_only(db_session: Session) -> None:
    invoice, _company, _contact, _taxes = make_full_package(db_session)
    accountant = _make_client_with_role(db_session, UserRole.ACCOUNTANT)
    try:
        forbidden = accountant.get(f"/api/v1/invoices/{invoice.id}/dian-preview")
        assert forbidden.status_code == 403, forbidden.text
    finally:
        _clear_overrides()

    admin = _make_client_with_role(db_session, UserRole.ADMIN)
    try:
        allowed = admin.get(f"/api/v1/invoices/{invoice.id}/dian-preview")
        assert allowed.status_code == 200, allowed.text
        body = allowed.json()
        assert len(body["cufe"]) == 96
        assert body["dian_status"] == "GENERADO_SIN_PIN"
        assert body["environment"] == "HABILITACION"
        assert "<Invoice" in body["xml"]
    finally:
        _clear_overrides()


def test_download_persists_cufe_and_status(db_session: Session) -> None:
    admin = _make_client_with_role(db_session, UserRole.ADMIN)
    try:
        invoice, _company, _contact, _taxes = make_full_package(db_session)
        assert invoice.cufe is None
        assert invoice.dian_status is None

        first = _download(admin, str(invoice.id), "xml")
        assert first.status_code == 200
        cufe = etree.fromstring(first.content).findtext(
            "{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}UUID"
        )
        db_session.expire_all()
        stored = db_session.get(type(invoice), invoice.id)
        assert stored is not None
        assert stored.cufe == cufe
        assert stored.dian_status is DianDocumentStatus.GENERADO_SIN_PIN
        assert stored.xml_generated_at is not None

        # Descargar de nuevo es idempotente: mismos bytes, misma marca de tiempo.
        before = stored.xml_generated_at
        second = _download(admin, str(invoice.id), "xml")
        assert second.status_code == 200
        assert second.content == first.content
        db_session.expire_all()
        stored = db_session.get(type(invoice), invoice.id)
        assert stored is not None
        assert stored.cufe == cufe
        assert stored.xml_generated_at == before
    finally:
        _clear_overrides()


def test_regenerate_cufe_with_real_pin_changes_status(db_session: Session) -> None:
    invoice, company, _contact, _taxes = make_full_package(db_session)
    admin = _make_client_with_role(db_session, UserRole.ADMIN)
    try:
        first = admin.post(f"/api/v1/invoices/{invoice.id}/regenerate-cufe")
        assert first.status_code == 200, first.text
        assert first.json()["dian_status"] == "GENERADO_SIN_PIN"

        company.dian_software_pin = "fc8eac422eba16e6523640285d54f33e8"
        db_session.flush()
        second = admin.post(f"/api/v1/invoices/{invoice.id}/regenerate-cufe")
        assert second.status_code == 200, second.text
        assert second.json()["dian_status"] == "GENERADO"
        assert second.json()["cufe"] != first.json()["cufe"]
    finally:
        _clear_overrides()
