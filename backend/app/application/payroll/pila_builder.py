"""Archivo plano PILA (Planilla Integrada de Liquidación de Aportantes).

Formato simplificado de registros separados por ``|``, alineado con la
estructura oficial de la PILA: Registro Tipo 1 (empleador), Tipo 2 (uno
por empleado), Tipo 3 (novedades — vacío en esta fase) y Tipo 4 (totales).

El layout posicional exacto por operador se ajusta en la fase de
transmisión (39B); esta fase garantiza los códigos (AFP, EPS, ARL, caja)
y los valores correctos por empleado.
"""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.domain.models.company_setting import CompanySetting
    from app.domain.models.payroll import (
        Employee,
        PayrollContribution,
        PayrollDetail,
        PayrollPeriod,
    )

ZERO = Decimal("0.00")


def _money(value: Decimal) -> str:
    return f"{value:.2f}"


def _row(*fields: object) -> str:
    return "|".join(str(field) for field in fields)


def build_pila_file(
    *,
    period: PayrollPeriod,
    company: CompanySetting,
    rows: list[tuple[PayrollDetail, PayrollContribution]],
    employees: dict[uuid.UUID, Employee],
    generated_at: date,
) -> str:
    """Archivo plano PILA del periodo (una línea por registro, \\n final)."""
    lines: list[str] = []

    # Registro Tipo 1: datos del empleador.
    lines.append(
        _row(
            "01",
            company.tax_id,
            company.dv,
            company.name,
            company.dian_municipality_code,
            f"{period.year}{period.month:02d}",
            "NEXUS-ERP-39A",
            generated_at.isoformat(),
        )
    )

    total_salud = ZERO
    total_pension = ZERO
    total_arl = ZERO

    # Registro Tipo 2: liquidación de cada empleado.
    for detail, contribution in rows:
        employee = employees[detail.employee_id]
        total_salud += detail.health_deduction + contribution.health_employer
        total_pension += detail.pension_deduction + contribution.pension_employer
        total_arl += contribution.arl_employer
        lines.append(
            _row(
                "02",
                employee.document_type or "CC",
                employee.document,
                f"{employee.first_name} {employee.last_name}",
                employee.eps_code,
                employee.afp_code,
                employee.arl_code,
                employee.compensation_fund_code,
                employee.risk_level or "I",
                _money(detail.base_salary),
                _money(detail.health_deduction),
                _money(contribution.health_employer),
                _money(detail.pension_deduction),
                _money(contribution.pension_employer),
                _money(contribution.arl_employer),
                _money(contribution.sena),
                _money(contribution.icbf),
                _money(contribution.compensation_fund),
            )
        )

    # Registro Tipo 3: novedades (vacío en esta fase).
    lines.append(_row("03"))

    # Registro Tipo 4: totales del periodo.
    lines.append(
        _row(
            "04",
            len(rows),
            _money(total_salud),
            _money(total_pension),
            _money(total_arl),
        )
    )

    return "\n".join(lines) + "\n"


__all__ = ["build_pila_file"]
