"""Tests del archivo plano PILA y del reporte UGPP."""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy.orm import Session

from app.application.payroll.pila_builder import build_pila_file
from app.application.payroll.ugpp_report import build_ugpp_report
from tests.payroll_dian_factories import make_payroll_package


def _context(db_session: Session):
    package = make_payroll_package(db_session)
    rows = [(package["detail"], package["contribution"])]
    employees = {package["employee"].id: package["employee"]}
    return package, rows, employees


def test_pila_file_registers_and_codes(db_session: Session) -> None:
    package, rows, employees = _context(db_session)
    pila = build_pila_file(
        period=package["period"],
        company=package["company"],
        rows=rows,
        employees=employees,
        generated_at=package["period"].payment_date,
    )
    lines = pila.strip().split("\n")

    assert len(lines) == 4  # Tipos 1, 2, 3 y 4.
    employer, employee, novelties, totals = lines

    fields = employer.split("|")
    assert fields[0] == "01"
    assert fields[1] == "900123456"  # NIT del empleador.
    assert fields[3] == "Nexus ERP S.A.S."
    assert fields[5] == "202610"

    fields = employee.split("|")
    assert fields[0] == "02"
    assert fields[3].startswith("Ana Pérez")
    assert fields[4] == "SANITAS"  # EPS
    assert fields[5] == "PORVIDA"  # AFP
    assert fields[6] == "POSITIVA"  # ARL
    assert fields[7] == "COMFAMA"  # Caja
    assert fields[8] == "II"  # Nivel de riesgo.
    assert fields[9] == "1000000.00"  # IBC.
    assert fields[10] == "40000.00"  # Salud empleado.
    assert fields[15] == "20000.00"  # SENA.

    assert novelties.split("|")[0] == "03"

    fields = totals.split("|")
    assert fields[0] == "04"
    assert fields[1] == "1"  # Un empleado.
    assert Decimal(fields[2]) == Decimal("85000.00")  # Salud total.
    assert Decimal(fields[3]) == Decimal("160000.00")  # Pensión total.
    assert Decimal(fields[4]) == Decimal("10440.00")  # ARL.

    assert pila.endswith("\n")


def test_ugpp_report_totals(db_session: Session) -> None:
    package, rows, employees = _context(db_session)
    report = build_ugpp_report(period=package["period"], rows=rows, employees=employees)
    assert report["period"]["year"] == 2026
    assert report["period"]["month"] == 10
    assert report["employee_count"] == 1

    entry = report["employees"][0]
    assert entry["employee_document"] == package["employee"].document
    assert entry["eps_code"] == "SANITAS"
    assert entry["risk_level"] == "II"

    totals = report["totals"]
    assert Decimal(totals["base_salary"]) == Decimal("1000000.00")
    assert Decimal(totals["health_employee"]) == Decimal("40000.00")
    assert Decimal(totals["pension_employer"]) == Decimal("120000.00")
    assert Decimal(totals["net_pay"]) == Decimal("920000.00")
    # Aportes del empleador: salud + pensión + ARL + SENA + ICBF + caja.
    assert Decimal(totals["total_aportes"]) == Decimal("265440.00")
