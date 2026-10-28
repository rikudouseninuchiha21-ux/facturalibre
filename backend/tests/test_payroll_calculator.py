"""Tests del calculador de aportes y prestaciones (Colombia, Decimal)."""

from __future__ import annotations

from decimal import Decimal

import pytest

from app.application.payroll.payroll_calculator import (
    compute_bonus,
    compute_contributions,
    compute_severance,
    compute_severance_interest,
    compute_vacation,
)

SALARY = Decimal("1000000.00")


def test_contributions_risk_ii() -> None:
    rates = compute_contributions(SALARY, "II")
    assert rates["health_employee"] == Decimal("40000.00")
    assert rates["health_employer"] == Decimal("45000.00")
    assert rates["pension_employee"] == Decimal("40000.00")
    assert rates["pension_employer"] == Decimal("120000.00")
    assert rates["arl_employer"] == Decimal("10440.00")
    assert rates["compensation_fund"] == Decimal("40000.00")
    assert rates["icbf"] == Decimal("30000.00")
    assert rates["sena"] == Decimal("20000.00")


def test_contributions_risk_v() -> None:
    assert compute_contributions(SALARY, "V")["arl_employer"] == Decimal("69600.00")


def test_contributions_invalid_risk_falls_back_to_level_i() -> None:
    assert compute_contributions(SALARY, "IX")["arl_employer"] == Decimal("5220.00")
    assert compute_contributions(SALARY, "")["arl_employer"] == Decimal("5220.00")


def test_severance_and_interest() -> None:
    severance = compute_severance(SALARY, 30)
    assert severance == Decimal("83333.33")
    assert compute_severance_interest(severance, 30) == Decimal("833.33")
    # Un año completo equivale a un mes de salario.
    assert compute_severance(SALARY, 360) == Decimal("1000000.00")


def test_vacation() -> None:
    # 15 días de salario al año: con 360 días es medio salario.
    assert compute_vacation(SALARY, 360) == Decimal("500000.00")
    assert compute_vacation(SALARY, 30) == Decimal("41666.67")


def test_bonus() -> None:
    # Prima de servicios: 30 días al año → un salario con el año completo.
    assert compute_bonus(SALARY, 360) == Decimal("1000000.00")
    assert compute_bonus(SALARY, 30) == Decimal("83333.33")


def test_results_are_quantized() -> None:
    rates = compute_contributions(Decimal("123.45"), "I")
    for value in rates.values():
        assert value == value.quantize(Decimal("0.01"))


@pytest.mark.parametrize("days", [0, 15, 180, 360])
def test_prestaciones_never_negative(days: int) -> None:
    assert compute_severance(SALARY, days) >= 0
    assert compute_vacation(SALARY, days) >= 0
    assert compute_bonus(SALARY, days) >= 0
