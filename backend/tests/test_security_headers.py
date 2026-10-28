"""Tests de las cabeceras de seguridad (Fase 39B)."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_endpoints_return_security_headers(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.headers["Content-Security-Policy"].startswith("default-src 'self'")
    assert "frame-ancestors 'none'" in response.headers["Content-Security-Policy"]
    assert "max-age=31536000" in response.headers["Strict-Transport-Security"]
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"


def test_headers_present_on_protected_endpoints(client: TestClient) -> None:
    response = client.get("/api/v1/contacts")
    assert response.status_code in (200, 401)
    assert response.headers["X-Frame-Options"] == "DENY"
