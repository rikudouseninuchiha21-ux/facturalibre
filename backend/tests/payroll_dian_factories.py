"""Fábricas ORM para los tests de Nómina Electrónica (Fase 39A).

Reutiliza la empresa DIAN del factory de facturas y crea directamente el
paquete de nómina (empleado con datos fiscales, periodo, detalle y
aportes) sin pasar por la API para aislar los builders.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any
from uuid import uuid4

from sqlalchemy.orm import Session

from app.domain.models.payroll import (
    Employee,
    PayrollContribution,
    PayrollDetail,
    PayrollPeriod,
    PayrollPeriodStatus,
)
from tests.dian_factories import make_company

ZERO = Decimal("0.00")


def make_dian_employee(db: Session, *, with_dian_data: bool = True) -> Employee:
    """Empleado con los datos fiscales del Anexo Técnico de nómina."""
    suffix = uuid4().hex[:6]
    employee = Employee(
        document=f"1{uuid4().int % 10**9:09d}",
        first_name="Ana",
        last_name=f"Pérez {suffix}",
        email=f"ana{suffix}@nexus.co",
        base_salary=Decimal("1000000.00"),
        start_date=date(2024, 1, 15),
        document_type="CC" if with_dian_data else None,
        address="Calle 100 # 8-50" if with_dian_data else None,
        municipality_code="11001" if with_dian_data else None,
        department_code="11" if with_dian_data else None,
        contract_type="INDEFINIDO" if with_dian_data else None,
        salary_type="ORDINARIO" if with_dian_data else None,
        risk_level="II" if with_dian_data else None,
        bank_account="123456789" if with_dian_data else None,
        afp_code="PORVIDA" if with_dian_data else None,
        eps_code="SANITAS" if with_dian_data else None,
        arl_code="POSITIVA" if with_dian_data else None,
        severance_fund_code="PROTECCION" if with_dian_data else None,
        compensation_fund_code="COMFAMA" if with_dian_data else None,
    )
    db.add(employee)
    db.flush()
    return employee


def make_payroll_package(
    db: Session,
    *,
    with_dian_data: bool = True,
    software_pin: str | None = "",
    period_status: PayrollPeriodStatus = PayrollPeriodStatus.CLOSED,
) -> dict[str, Any]:
    """Empresa + empleado + periodo liquidado con sus aportes.

    Salario 1.000.000 (riesgo II): salud/pensión empleado 40.000 c/u,
    neto 920.000; aportes empleador: salud 45.000, pensión 120.000,
    ARL 10.440, caja 40.000, ICBF 30.000, SENA 20.000.
    """
    company = make_company(db, software_pin=software_pin)
    employee = make_dian_employee(db, with_dian_data=with_dian_data)

    period = PayrollPeriod(
        month=10,
        year=2026,
        status=period_status,
        payment_date=date(2026, 10, 31),
        notes_dian="Nómina de prueba",
        created_at=datetime(2026, 10, 31, 20, 0, 0, tzinfo=UTC),
    )
    db.add(period)
    db.flush()

    detail = PayrollDetail(
        period_id=period.id,
        employee_id=employee.id,
        base_salary=Decimal("1000000.00"),
        health_deduction=Decimal("40000.00"),
        pension_deduction=Decimal("40000.00"),
        net_pay=Decimal("920000.00"),
    )
    contribution = PayrollContribution(
        detail=detail,
        period_id=period.id,
        health_employee=Decimal("40000.00"),
        health_employer=Decimal("45000.00"),
        pension_employee=Decimal("40000.00"),
        pension_employer=Decimal("120000.00"),
        arl_employer=Decimal("10440.00"),
        compensation_fund=Decimal("40000.00"),
        icbf=Decimal("30000.00"),
        sena=Decimal("20000.00"),
        severance=Decimal("83333.33"),
        severance_interest=Decimal("833.33"),
        vacation=Decimal("41666.67"),
        bonus=Decimal("83333.33"),
    )
    db.add_all([detail, contribution])
    db.flush()
    return {
        "company": company,
        "employee": employee,
        "period": period,
        "detail": detail,
        "contribution": contribution,
    }


__all__ = ["make_dian_employee", "make_payroll_package"]
