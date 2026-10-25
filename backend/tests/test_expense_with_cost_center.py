"""Integración: el gasto propaga su centro de costo a las líneas del asiento."""

from __future__ import annotations

from datetime import date
from typing import Any
from uuid import uuid4

from fastapi.testclient import TestClient


def _create_cost_center(client: TestClient) -> str:
    response = client.post(
        "/api/v1/cost-centers",
        json={"code": f"CC-{uuid4().hex[:8].upper()}", "name": "Administración"},
    )
    assert response.status_code == 201, response.text
    return str(response.json()["id"])


def _expense_payload(cost_center_id: str | None) -> dict[str, object]:
    payload: dict[str, object] = {
        "date": date.today().isoformat(),
        "concept": "Arriendo administrativo",
        "amount": "1850000.00",
        "payment_method": "efectivo",
    }
    if cost_center_id is not None:
        payload["cost_center_id"] = cost_center_id
    return payload


def _expense_entry(client: TestClient, expense_id: str) -> dict[str, Any]:
    entries = client.get("/api/v1/accounting/entries?limit=100")
    assert entries.status_code == 200, entries.text
    matches = [
        entry
        for entry in entries.json()
        if entry["source_type"] == "EXPENSE" and entry["source_id"] == expense_id
    ]
    assert len(matches) == 1
    return matches[0]


def test_expense_propagates_cost_center_to_entry_lines(client: TestClient) -> None:
    cost_center_id = _create_cost_center(client)

    created = client.post("/api/v1/expenses", json=_expense_payload(cost_center_id))
    assert created.status_code == 201, created.text
    assert created.json()["cost_center_id"] == cost_center_id

    entry = _expense_entry(client, created.json()["id"])
    assert len(entry["lines"]) == 2
    for line in entry["lines"]:
        assert line["cost_center_id"] == cost_center_id


def test_expense_without_cost_center_keeps_null(client: TestClient) -> None:
    created = client.post("/api/v1/expenses", json=_expense_payload(None))
    assert created.status_code == 201, created.text
    assert created.json()["cost_center_id"] is None

    entry = _expense_entry(client, created.json()["id"])
    for line in entry["lines"]:
        assert line["cost_center_id"] is None


def test_expense_with_invalid_cost_center_returns_404(client: TestClient) -> None:
    payload = _expense_payload(str(uuid4()))
    response = client.post("/api/v1/expenses", json=payload)
    assert response.status_code == 404, response.text
    assert "Centro de costo" in response.json()["detail"]
