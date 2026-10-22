"""Tests del núcleo de empleados y de la liquidación básica de nómina."""

from __future__ import annotations

from decimal import Decimal
from typing import Any
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.application.accounting.service import AccountingError
from app.domain.models.accounting import AccountingAccount, AccountingEntry
from app.domain.models.payroll import Employee, PayrollDetail

TWOPLACES = Decimal("0.01")
ZERO = Decimal("0.00")


def _money(value: object) -> Decimal:
    return Decimal(str(value)).quantize(TWOPLACES)


def _create_employee(
    client: TestClient,
    *,
    document: str | None = None,
    first_name: str = "Ana",
    last_name: str = "Pérez",
    base_salary: str = "123.45",
    is_active: bool = True,
) -> dict[str, Any]:
    response = client.post(
        "/api/v1/employees",
        json={
            "document": document or str(uuid4()),
            "first_name": first_name,
            "last_name": last_name,
            "email": "ana.perez@example.com",
            "base_salary": base_salary,
            "start_date": "2026-01-15",
            "is_active": is_active,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def _create_period(
    client: TestClient,
    *,
    month: int = 10,
    year: int = 2026,
) -> dict[str, Any]:
    response = client.post(
        "/api/v1/payroll/periods",
        json={"month": month, "year": year},
    )
    assert response.status_code == 201, response.text
    return response.json()


def _calculate(client: TestClient, period_id: object) -> dict[str, Any]:
    response = client.post(f"/api/v1/payroll/periods/{period_id}/calculate")
    assert response.status_code == 200, response.text
    return response.json()


def _payroll_entry(client: TestClient, period_id: object) -> dict[str, Any]:
    response = client.get("/api/v1/accounting/entries?limit=100")
    assert response.status_code == 200, response.text
    matches = [
        entry
        for entry in response.json()
        if entry["source_type"] == "PAYROLL" and entry["source_id"] == period_id
    ]
    assert len(matches) == 1
    return matches[0]


def _lines_by_code(entry: dict[str, Any]) -> dict[str, dict[str, Any]]:
    lines = entry["lines"]
    assert isinstance(lines, list)
    return {str(line["account_code"]): line for line in lines}


def test_create_employee_and_list(client: TestClient) -> None:
    employee = _create_employee(client, document="CC-1001")

    assert employee["document"] == "CC-1001"
    assert employee["first_name"] == "Ana"
    assert employee["last_name"] == "Pérez"
    assert _money(employee["base_salary"]) == Decimal("123.45")
    assert employee["is_active"] is True

    listed = client.get("/api/v1/employees?is_active=true")
    assert listed.status_code == 200, listed.text
    assert [item["id"] for item in listed.json()] == [employee["id"]]


def test_duplicate_employee_document_returns_409(client: TestClient) -> None:
    _create_employee(client, document="CC-1002")

    response = client.post(
        "/api/v1/employees",
        json={
            "document": "CC-1002",
            "first_name": "Otra",
            "last_name": "Persona",
            "base_salary": "100.00",
            "start_date": "2026-02-01",
        },
    )

    assert response.status_code == 409
    assert response.json() == {"detail": "El documento del empleado ya existe"}


def test_calculate_period_uses_decimal_and_round_half_up(client: TestClient) -> None:
    employee = _create_employee(client, document="CC-1003", base_salary="123.45")
    period = _create_period(client)

    assert period["status"] == "DRAFT"
    assert period["details"] == []

    calculated = _calculate(client, period["id"])

    assert calculated["status"] == "CLOSED"
    assert len(calculated["details"]) == 1
    detail = calculated["details"][0]
    assert detail["employee_id"] == employee["id"]
    assert detail["employee_name"] == "Ana Pérez"
    assert _money(detail["base_salary"]) == Decimal("123.45")
    assert _money(detail["health_deduction"]) == Decimal("4.94")
    assert _money(detail["pension_deduction"]) == Decimal("4.94")
    assert _money(detail["net_pay"]) == Decimal("113.57")
    assert _money(calculated["total_base"]) == Decimal("123.45")
    assert _money(calculated["total_health"]) == Decimal("4.94")
    assert _money(calculated["total_pension"]) == Decimal("4.94")
    assert _money(calculated["total_net"]) == Decimal("113.57")

    fetched = client.get(f"/api/v1/payroll/periods/{period['id']}")
    assert fetched.status_code == 200, fetched.text
    assert fetched.json() == calculated


def test_calculation_excludes_inactive_employees(client: TestClient) -> None:
    _create_employee(
        client,
        document="CC-2001",
        first_name="Activo",
        last_name="Uno",
        base_salary="1000.00",
    )
    _create_employee(
        client,
        document="CC-2002",
        first_name="Activo",
        last_name="Dos",
        base_salary="500.00",
    )
    _create_employee(
        client,
        document="CC-2003",
        first_name="Inactivo",
        last_name="Tres",
        base_salary="999.00",
        is_active=False,
    )
    period = _create_period(client)

    calculated = _calculate(client, period["id"])

    assert len(calculated["details"]) == 2
    assert _money(calculated["total_base"]) == Decimal("1500.00")
    assert _money(calculated["total_health"]) == Decimal("60.00")
    assert _money(calculated["total_pension"]) == Decimal("60.00")
    assert _money(calculated["total_net"]) == Decimal("1380.00")


def test_calculation_generates_balanced_accounting_entry(client: TestClient) -> None:
    _create_employee(client, document="CC-3001", base_salary="123.45")
    period = _create_period(client)
    _calculate(client, period["id"])

    entry = _payroll_entry(client, period["id"])
    lines = _lines_by_code(entry)

    assert entry["entry_date"] == "2026-10-31"
    assert entry["description"] == "Liquidación de nómina 10/2026"
    assert _money(entry["total_debit"]) == Decimal("123.45")
    assert _money(entry["total_credit"]) == Decimal("123.45")

    assert _money(lines["510506"]["debit"]) == Decimal("123.45")
    assert _money(lines["510506"]["credit"]) == ZERO
    assert _money(lines["250505"]["debit"]) == ZERO
    assert _money(lines["250505"]["credit"]) == Decimal("113.57")
    assert _money(lines["237005"]["debit"]) == ZERO
    assert _money(lines["237005"]["credit"]) == Decimal("9.88")


def test_calculate_twice_returns_409(client: TestClient) -> None:
    _create_employee(client, document="CC-4001")
    period = _create_period(client)
    _calculate(client, period["id"])

    repeated = client.post(f"/api/v1/payroll/periods/{period['id']}/calculate")

    assert repeated.status_code == 409
    assert repeated.json() == {"detail": "El periodo de nómina ya está cerrado"}


def test_duplicate_period_returns_409(client: TestClient) -> None:
    _create_period(client, month=11, year=2026)

    response = client.post(
        "/api/v1/payroll/periods",
        json={"month": 11, "year": 2026},
    )

    assert response.status_code == 409
    assert response.json() == {"detail": "Ya existe un periodo de nómina para ese mes y año"}


def test_calculate_without_active_employees_returns_409(client: TestClient) -> None:
    period = _create_period(client)

    response = client.post(f"/api/v1/payroll/periods/{period['id']}/calculate")

    assert response.status_code == 409
    assert response.json() == {"detail": "No hay empleados activos para liquidar"}


def test_calculate_missing_period_returns_404(client: TestClient) -> None:
    response = client.post(f"/api/v1/payroll/periods/{uuid4()}/calculate")

    assert response.status_code == 404
    assert response.json() == {"detail": "Periodo de nómina no encontrado"}


def test_calculation_rolls_back_if_accounting_fails(
    client: TestClient,
    db_session: Session,
) -> None:
    _create_employee(client, document="CC-5001", base_salary="123.45")
    period = _create_period(client)

    db_session.execute(delete(AccountingAccount).where(AccountingAccount.code == "250505"))
    db_session.flush()

    with pytest.raises(AccountingError):
        client.post(f"/api/v1/payroll/periods/{period['id']}/calculate")

    unchanged = client.get(f"/api/v1/payroll/periods/{period['id']}")
    assert unchanged.status_code == 200, unchanged.text
    assert unchanged.json()["status"] == "DRAFT"
    assert unchanged.json()["details"] == []
    assert (
        db_session.scalar(
            select(func.count())
            .select_from(PayrollDetail)
            .where(PayrollDetail.period_id == period["id"])
        )
        == 0
    )
    assert (
        db_session.scalar(
            select(func.count())
            .select_from(AccountingEntry)
            .where(AccountingEntry.source_id == period["id"])
        )
        == 0
    )


def test_deactivate_employee_is_soft_delete(client: TestClient) -> None:
    employee = _create_employee(client, document="CC-6001")

    deleted = client.delete(f"/api/v1/employees/{employee['id']}")
    assert deleted.status_code == 204

    fetched = client.get(f"/api/v1/employees/{employee['id']}")
    assert fetched.status_code == 200, fetched.text
    assert fetched.json()["is_active"] is False

    visible = client.get("/api/v1/employees?is_active=true")
    assert visible.status_code == 200
    assert all(item["id"] != employee["id"] for item in visible.json())


def test_employee_model_is_persisted(client: TestClient, db_session: Session) -> None:
    employee = _create_employee(client, document="CC-7001")

    stored = db_session.get(Employee, employee["id"])
    assert stored is not None
    assert stored.document == "CC-7001"
    assert stored.base_salary == Decimal("123.45")
