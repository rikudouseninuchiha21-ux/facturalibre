"""Integración: la nómina propaga su centro de costo a las líneas del asiento."""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from fastapi.testclient import TestClient


def _create_cost_center(client: TestClient) -> str:
    response = client.post(
        "/api/v1/cost-centers",
        json={"code": f"CC-{uuid4().hex[:8].upper()}", "name": "Nómina"},
    )
    assert response.status_code == 201, response.text
    return str(response.json()["id"])


def _create_employee(client: TestClient, document: str) -> dict[str, Any]:
    response = client.post(
        "/api/v1/employees",
        json={
            "document": document,
            "first_name": "Ana",
            "last_name": "Empleado",
            "base_salary": "123.45",
            "start_date": "2026-01-01",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def _create_period(client: TestClient, cost_center_id: str | None) -> dict[str, Any]:
    payload: dict[str, Any] = {"month": 10, "year": 2026}
    if cost_center_id is not None:
        payload["cost_center_id"] = cost_center_id
    response = client.post("/api/v1/payroll/periods", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def _payroll_entry(client: TestClient, period_id: str) -> dict[str, Any]:
    entries = client.get("/api/v1/accounting/entries?limit=100")
    assert entries.status_code == 200, entries.text
    matches = [
        entry
        for entry in entries.json()
        if entry["source_type"] == "PAYROLL" and entry["source_id"] == period_id
    ]
    assert len(matches) == 1
    return matches[0]


def test_payroll_propagates_cost_center_to_entry_lines(client: TestClient) -> None:
    cost_center_id = _create_cost_center(client)
    _create_employee(client, document=f"CC-{uuid4().hex[:8].upper()}")

    period = _create_period(client, cost_center_id)
    assert period["cost_center_id"] == cost_center_id

    calculated = client.post(f"/api/v1/payroll/periods/{period['id']}/calculate")
    assert calculated.status_code == 200, calculated.text

    entry = _payroll_entry(client, period["id"])
    assert len(entry["lines"]) >= 2
    for line in entry["lines"]:
        assert line["cost_center_id"] == cost_center_id


def test_payroll_with_invalid_cost_center_returns_422(client: TestClient) -> None:
    response = client.post(
        "/api/v1/payroll/periods",
        json={"month": 11, "year": 2026, "cost_center_id": str(uuid4())},
    )
    assert response.status_code == 422, response.text
    assert "cost_center_id" in response.json()["detail"]
