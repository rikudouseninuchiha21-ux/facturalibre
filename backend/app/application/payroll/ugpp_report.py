"""Reporte UGPP: resumen de aportes por empleado y totales del periodo."""

from __future__ import annotations

import uuid
from decimal import Decimal
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.domain.models.payroll import (
        Employee,
        PayrollContribution,
        PayrollDetail,
        PayrollPeriod,
    )

ZERO = Decimal("0.00")


def _entry(
    detail: PayrollDetail,
    contribution: PayrollContribution,
    employee: Employee,
) -> dict[str, Any]:
    return {
        "employee_id": str(employee.id),
        "employee_document": employee.document,
        "employee_name": f"{employee.first_name} {employee.last_name}",
        "eps_code": employee.eps_code,
        "afp_code": employee.afp_code,
        "arl_code": employee.arl_code,
        "risk_level": employee.risk_level or "I",
        "base_salary": str(detail.base_salary),
        "health_employee": str(contribution.health_employee),
        "health_employer": str(contribution.health_employer),
        "pension_employee": str(contribution.pension_employee),
        "pension_employer": str(contribution.pension_employer),
        "arl_employer": str(contribution.arl_employer),
        "sena": str(contribution.sena),
        "icbf": str(contribution.icbf),
        "compensation_fund": str(contribution.compensation_fund),
        "total_aportes": str(contribution.total_employer_contributions),
        "net_pay": str(detail.net_pay),
    }


def build_ugpp_report(
    *,
    period: PayrollPeriod,
    rows: list[tuple[PayrollDetail, PayrollContribution]],
    employees: dict[uuid.UUID, Employee],
) -> dict[str, Any]:
    """Resumen de aportes por empleado y totales para el reporte UGPP."""
    entries = [
        _entry(detail, contribution, employees[detail.employee_id]) for detail, contribution in rows
    ]
    totals: dict[str, Decimal] = {}
    for entry in entries:
        for key in (
            "base_salary",
            "health_employee",
            "health_employer",
            "pension_employee",
            "pension_employer",
            "arl_employer",
            "sena",
            "icbf",
            "compensation_fund",
            "total_aportes",
            "net_pay",
        ):
            totals[key] = totals.get(key, ZERO) + Decimal(entry[key])

    return {
        "period": {"year": period.year, "month": period.month, "id": str(period.id)},
        "employees": entries,
        "totals": {key: str(value) for key, value in totals.items()},
        "employee_count": len(entries),
    }


__all__ = ["build_ugpp_report"]
