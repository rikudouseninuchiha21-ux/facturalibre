"""Tests del módulo de activos fijos y depreciación por línea recta."""

from __future__ import annotations

import calendar
from datetime import date
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.application.accounting.service import AccountingError
from app.domain.models.accounting import AccountingAccount, AccountingEntry
from app.domain.models.fixed_asset import (
    DepreciationEntry,
    FixedAsset,
    FixedAssetStatus,
)

TWOPLACES = Decimal("0.01")


def _money(value: object) -> Decimal:
    return Decimal(str(value)).quantize(TWOPLACES)


def _create_asset(
    client: TestClient,
    *,
    code: str = "VEH-001",
    name: str = "Camioneta de reparto",
    initial_cost: str = "1200000.00",
    salvage_value: str = "0.00",
    useful_life_months: int = 12,
    purchase_date: str = "2020-01-01",
) -> dict[str, Any]:
    response = client.post(
        "/api/v1/assets",
        json={
            "code": code,
            "name": name,
            "purchase_date": purchase_date,
            "initial_cost": initial_cost,
            "salvage_value": salvage_value,
            "useful_life_months": useful_life_months,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def _entry_for(
    client: TestClient,
    source_type: str,
    source_id: object,
) -> dict[str, Any]:
    response = client.get("/api/v1/accounting/entries?limit=100")
    assert response.status_code == 200, response.text
    matches = [
        entry
        for entry in response.json()
        if entry["source_type"] == source_type and entry["source_id"] == source_id
    ]
    assert len(matches) == 1
    return matches[0]


def _lines_by_code(entry: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {str(line["account_code"]): line for line in entry["lines"]}


def _depreciate(
    client: TestClient,
    asset_id: object,
    *,
    year: int | None = None,
    month: int | None = None,
) -> Any:
    today = date.today()
    return client.post(
        f"/api/v1/assets/{asset_id}/depreciate",
        json={
            "year": today.year if year is None else year,
            "month": today.month if month is None else month,
        },
    )


def test_create_asset_returns_calculated_values(client: TestClient) -> None:
    asset = _create_asset(client)

    assert asset["code"] == "VEH-001"
    assert asset["status"] == "ACTIVE"
    assert _money(asset["initial_cost"]) == Decimal("1200000.00")
    assert _money(asset["salvage_value"]) == Decimal("0.00")
    assert asset["useful_life_months"] == 12
    assert _money(asset["monthly_depreciation"]) == Decimal("100000.00")
    assert _money(asset["accumulated_depreciation"]) == Decimal("0.00")
    assert _money(asset["current_value"]) == Decimal("1200000.00")
    assert asset["is_fully_depreciated"] is False


def test_create_asset_trims_code_and_rejects_duplicates(client: TestClient) -> None:
    asset = _create_asset(client, code="  veh-002  ")
    assert asset["code"] == "veh-002"

    duplicate = client.post(
        "/api/v1/assets",
        json={
            "code": "veh-002",
            "name": "Otro activo",
            "purchase_date": "2020-01-01",
            "initial_cost": "100.00",
            "salvage_value": "0.00",
            "useful_life_months": 10,
        },
    )
    assert duplicate.status_code == 409, duplicate.text


def test_create_asset_rejects_salvage_not_less_than_cost(client: TestClient) -> None:
    response = client.post(
        "/api/v1/assets",
        json={
            "code": "VEH-003",
            "name": "Activo inválido",
            "purchase_date": "2020-01-01",
            "initial_cost": "1000.00",
            "salvage_value": "1000.00",
            "useful_life_months": 10,
        },
    )
    assert response.status_code == 422, response.text


def test_list_assets_returns_accumulated_and_current_value(
    client: TestClient,
) -> None:
    _create_asset(client, code="VEH-010", initial_cost="1000.00", useful_life_months=10)
    _create_asset(client, code="VEH-011", initial_cost="2000.00", useful_life_months=10)

    response = client.get("/api/v1/assets")
    assert response.status_code == 200, response.text
    assets = {asset["code"]: asset for asset in response.json()}

    assert _money(assets["VEH-010"]["current_value"]) == Decimal("1000.00")
    assert _money(assets["VEH-011"]["accumulated_depreciation"]) == Decimal("0.00")


def test_depreciate_creates_entry_and_updates_asset(
    client: TestClient,
    db_session: Session,
) -> None:
    asset = _create_asset(client)
    today = date.today()

    response = _depreciate(client, asset["id"])
    assert response.status_code == 200, response.text
    updated = response.json()

    assert _money(updated["accumulated_depreciation"]) == Decimal("100000.00")
    assert _money(updated["current_value"]) == Decimal("1100000.00")
    assert updated["is_fully_depreciated"] is False

    depreciation = db_session.scalar(
        select(DepreciationEntry).where(DepreciationEntry.asset_id == UUID(str(asset["id"])))
    )
    assert depreciation is not None
    assert depreciation.date == date(
        today.year,
        today.month,
        calendar.monthrange(today.year, today.month)[1],
    )
    assert _money(depreciation.amount) == Decimal("100000.00")
    assert depreciation.accounting_entry_id is not None

    entry = _entry_for(client, "DEPRECIATION", str(depreciation.id))
    lines = _lines_by_code(entry)
    assert _money(lines["5160"]["debit"]) == Decimal("100000.00")
    assert _money(lines["5160"]["credit"]) == Decimal("0.00")
    assert _money(lines["1592"]["debit"]) == Decimal("0.00")
    assert _money(lines["1592"]["credit"]) == Decimal("100000.00")
    assert _money(entry["total_debit"]) == _money(entry["total_credit"])


def test_depreciation_keeps_balance_sheet_balanced(client: TestClient) -> None:
    asset = _create_asset(client, code="VEH-BALANCE")
    response = _depreciate(client, asset["id"])
    assert response.status_code == 200, response.text

    report = client.get("/api/v1/reports/balance-sheet")
    assert report.status_code == 200, report.text
    data = report.json()

    assert data["balanced"] is True
    assets = {row["code"]: row for row in data["asset_accounts"]}
    assert _money(assets["1592"]["balance"]) == Decimal("-100000.00")


def test_depreciate_duplicate_month_returns_conflict(
    client: TestClient,
    db_session: Session,
) -> None:
    asset = _create_asset(client)

    first = _depreciate(client, asset["id"])
    assert first.status_code == 200, first.text

    second = _depreciate(client, asset["id"])
    assert second.status_code == 409, second.text
    assert "ya fue depreciado" in second.json()["detail"]

    count = db_session.scalar(select(func.count()).select_from(DepreciationEntry))
    assert count == 1


def test_depreciate_disposed_asset_returns_conflict(
    client: TestClient,
    db_session: Session,
) -> None:
    asset = _create_asset(client, code="VEH-DISPOSED")
    db_asset = db_session.get(FixedAsset, UUID(str(asset["id"])))
    assert db_asset is not None
    db_asset.status = FixedAssetStatus.DISPOSED
    db_session.flush()

    response = _depreciate(client, asset["id"])
    assert response.status_code == 409, response.text
    assert "ACTIVE" in response.json()["detail"]


def test_depreciate_missing_asset_returns_not_found(client: TestClient) -> None:
    response = _depreciate(client, uuid4())
    assert response.status_code == 404, response.text


def test_depreciation_is_atomic_if_accounting_fails(
    client: TestClient,
    db_session: Session,
) -> None:
    asset = _create_asset(client, code="VEH-ATOMIC")
    db_session.execute(delete(AccountingAccount).where(AccountingAccount.code == "5160"))
    db_session.flush()

    with pytest.raises(AccountingError):
        _depreciate(client, asset["id"])

    assert db_session.scalar(select(func.count()).select_from(DepreciationEntry)) == 0
    assert db_session.scalar(select(func.count()).select_from(AccountingEntry)) == 0


def test_final_depreciation_does_not_exceed_depreciable_base(
    client: TestClient,
) -> None:
    asset = _create_asset(
        client,
        code="VEH-FINAL",
        initial_cost="1000.00",
        salvage_value="100.00",
        useful_life_months=3,
    )
    first = _depreciate(client, asset["id"], year=2025, month=1)
    assert first.status_code == 200, first.text
    assert _money(first.json()["accumulated_depreciation"]) == Decimal("300.00")

    second = _depreciate(client, asset["id"], year=2025, month=2)
    assert second.status_code == 200, second.text
    assert _money(second.json()["accumulated_depreciation"]) == Decimal("600.00")

    third = _depreciate(client, asset["id"], year=2025, month=3)
    assert third.status_code == 200, third.text
    assert _money(third.json()["accumulated_depreciation"]) == Decimal("900.00")
    assert _money(third.json()["current_value"]) == Decimal("100.00")
    assert third.json()["is_fully_depreciated"] is True
