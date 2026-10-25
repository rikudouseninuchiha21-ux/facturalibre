"""Tests del cierre automático de presupuestos al cerrar el periodo fiscal."""

from __future__ import annotations

import logging
from datetime import date
from decimal import Decimal
from typing import Any
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.application.budget_service import BudgetService
from app.domain.models.accounting import (
    AccountingEntry,
    AccountingEntryLine,
    AccountingEntryStatus,
    AccountingSourceType,
)

ZERO = Decimal("0.00")

# Periodo del test: marzo de 2026 (abierto en la base de prueba).
TEST_YEAR = 2026
TEST_MONTH = 3


def _make_budget(
    client: TestClient,
    *,
    month: int = TEST_MONTH,
    approve: bool = True,
) -> dict[str, Any]:
    """Crea centro + presupuesto de una línea y lo aprueba si se pide."""
    center = client.post(
        "/api/v1/cost-centers",
        json={"code": f"CC-{uuid4().hex[:8].upper()}", "name": "Auto cierre"},
    )
    assert center.status_code == 201, center.text
    center = center.json()

    budget = client.post(
        "/api/v1/budgets",
        json={
            "cost_center_id": center["id"],
            "period_year": TEST_YEAR,
            "period_month": month,
        },
    )
    assert budget.status_code == 201, budget.text
    budget = budget.json()

    line = client.post(
        f"/api/v1/budgets/{budget['id']}/lines",
        json={"account_code": "5199", "amount": "1000.00"},
    )
    assert line.status_code == 201, line.text

    if approve:
        approved = client.post(f"/api/v1/budgets/{budget['id']}/approve")
        assert approved.status_code == 200, approved.text

    return budget


def _budget_status(client: TestClient, budget_id: str) -> str:
    response = client.get(f"/api/v1/budgets/{budget_id}")
    assert response.status_code == 200, response.text
    return str(response.json()["status"])


def _close_period(client: TestClient, month: int) -> Any:
    return client.post(
        "/api/v1/accounting/close-period",
        json={"month": month, "year": TEST_YEAR},
    )


def test_close_period_closes_approved_budgets_of_the_month(
    client: TestClient,
) -> None:
    """Cerrar el periodo cierra los APPROVED del mes; DRAFT y otros meses no."""
    approved_same_month = _make_budget(client, month=TEST_MONTH)
    draft_same_month = _make_budget(client, month=TEST_MONTH, approve=False)
    approved_other_month = _make_budget(client, month=TEST_MONTH + 1)

    closed = _close_period(client, TEST_MONTH)
    assert closed.status_code == 200, closed.text

    assert _budget_status(client, approved_same_month["id"]) == "CLOSED"
    assert _budget_status(client, draft_same_month["id"]) == "DRAFT"
    assert _budget_status(client, approved_other_month["id"]) == "APPROVED"


def test_close_by_period_is_idempotent(
    client: TestClient,
    db_session: Session,
) -> None:
    """La segunda llamada de close_by_period retorna 0 sin error."""
    budget = _make_budget(client)
    service = BudgetService(db_session)

    first = service.close_by_period(period_year=TEST_YEAR, period_month=TEST_MONTH)
    assert first == 1
    assert _budget_status(client, budget["id"]) == "CLOSED"

    second = service.close_by_period(period_year=TEST_YEAR, period_month=TEST_MONTH)
    assert second == 0


def test_close_by_period_without_budgets_returns_zero(
    client: TestClient,
    db_session: Session,
) -> None:
    """No hay presupuestos APPROVED: retorna 0 sin error."""
    service = BudgetService(db_session)
    result = service.close_by_period(period_year=TEST_YEAR, period_month=TEST_MONTH)
    assert result == 0


def test_close_period_failure_keeps_budgets_untouched(
    client: TestClient,
    db_session: Session,
) -> None:
    """Si el cierre del periodo falla, ningún presupuesto cambia de estado."""
    approved = _make_budget(client)

    # Asiento descuadrado en el mes: el cierre del periodo debe fallar (409)
    # y el presupuesto permanecer APPROVED por la transacción atómica.
    unbalanced = AccountingEntry(
        entry_date=date(TEST_YEAR, TEST_MONTH, 15),
        description="Asiento descuadrado de prueba",
        source_type=AccountingSourceType.INVOICE,
        source_id=uuid4(),
        status=AccountingEntryStatus.POSTED,
        lines=[
            AccountingEntryLine(
                account_code="5199",
                debit=Decimal("10.00"),
                credit=ZERO,
            )
        ],
    )
    db_session.add(unbalanced)
    db_session.flush()

    failed = _close_period(client, TEST_MONTH)
    assert failed.status_code == 409, failed.text
    assert "descuadrados" in failed.json()["detail"].lower()

    assert _budget_status(client, approved["id"]) == "APPROVED"


def test_close_period_logs_auto_closed_budgets(
    client: TestClient,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """El cierre emite budgets_auto_closed=N en el logger del proyecto."""
    _make_budget(client)

    with caplog.at_level(logging.INFO, logger="app.application.accounting.period_service"):
        closed = _close_period(client, TEST_MONTH)
    assert closed.status_code == 200, closed.text

    assert "budgets_auto_closed=1" in caplog.text
