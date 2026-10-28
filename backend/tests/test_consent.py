"""Tests del registro de consentimientos GDPR/CCPA (Fase 39B)."""

from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.models.consent import UserConsent


def test_register_consent_anonymous(anonymous_client: TestClient, db_session: Session) -> None:
    response = anonymous_client.post(
        "/api/v1/consent",
        json={"consent_type": "cookies_analytics", "is_granted": True},
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["consent_type"] == "cookies_analytics"
    assert body["is_granted"] is True

    stored = db_session.scalars(select(UserConsent).where(UserConsent.id == body["id"])).all()
    assert len(stored) == 1
    assert stored[0].user_id is None
    assert stored[0].ip_address is not None


def test_register_rejection(anonymous_client: TestClient) -> None:
    response = anonymous_client.post(
        "/api/v1/consent",
        json={"consent_type": "cookies_marketing", "is_granted": False},
    )
    assert response.status_code == 201
    assert response.json()["is_granted"] is False


def test_invalid_consent_type_returns_422(anonymous_client: TestClient) -> None:
    response = anonymous_client.post(
        "/api/v1/consent",
        json={"consent_type": "cookies_spyware"},
    )
    assert response.status_code == 422


def test_privacy_policy_is_public(anonymous_client: TestClient) -> None:
    policy = anonymous_client.get("/api/v1/privacy-policy")
    assert policy.status_code == 200
    assert "Política de Privacidad" in policy.json()["body"]

    terms = anonymous_client.get("/api/v1/terms")
    assert terms.status_code == 200
    assert "Términos y Condiciones" in terms.json()["body"]
