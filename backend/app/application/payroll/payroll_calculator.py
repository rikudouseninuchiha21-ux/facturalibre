"""Cálculo puro de aportes, parafiscales y prestaciones sociales (Colombia).

Todo con ``Decimal`` y cuantizado a 2 decimales con ROUND_HALF_UP.
REQUIERE VALIDACIÓN: experto en nómina colombiana. Aquí se implementan las
reglas del estándar general (Decreto 1601 de 2020 / PILA): no hay topes de
IBC, exoneraciones ni retención en la fuente; eso queda para fases
siguientes y está documentado en ``payroll/service.py``.
"""

from __future__ import annotations

from decimal import Decimal

from app.domain.calculations import round_money

HUNDRED = Decimal("100")

# Seguridad social.
HEALTH_EMPLOYEE_RATE = Decimal("0.04")  # 4 % del salario
HEALTH_EMPLOYER_RATE = Decimal("0.045")  # 4.5 %
PENSION_EMPLOYEE_RATE = Decimal("0.04")  # 4 %
PENSION_EMPLOYER_RATE = Decimal("0.12")  # 12 %

# Parafiscales (solo empleador).
SENA_RATE = Decimal("0.02")  # 2 %
ICBF_RATE = Decimal("0.03")  # 3 %
COMPENSATION_FUND_RATE = Decimal("0.04")  # 4 % (caja de compensación)

# ARL por nivel de riesgo (Decreto 564 de 2015, tabla VII).
ARL_RATES: dict[str, Decimal] = {
    "I": Decimal("0.00522"),
    "II": Decimal("0.01044"),
    "III": Decimal("0.02436"),
    "IV": Decimal("0.04350"),
    "V": Decimal("0.06960"),
}
DEFAULT_RISK_LEVEL = "I"

# Prestaciones sociales.
SEVERANCE_ANNUAL_RATE = Decimal("1") / Decimal("12")  # 8.33 % (1 mes por año)
SEVERANCE_INTEREST_MONTHLY_RATE = Decimal("0.01")  # 1 % mensual
VACATION_DAYS_PER_YEAR = 15
BONUS_DAYS_PER_YEAR = 30
DAYS_PER_YEAR = Decimal("360")
DAYS_PER_MONTH = Decimal("30")


def _rate(salary: Decimal, rate: Decimal) -> Decimal:
    return round_money(salary * rate)


def compute_contributions(salary: Decimal, risk_level: str) -> dict[str, Decimal]:
    """Aportes de seguridad social y parafiscales sobre el salario.

    - Salud: 8.5 % total (4 % empleado + 4.5 % empleador).
    - Pensión: 16 % total (4 % empleado + 12 % empleador).
    - ARL: solo empleador, según el nivel de riesgo (0.522 % a 6.96 %).
    - Parafiscales (empleador): SENA 2 %, ICBF 3 %, caja 4 %.
    """
    level = risk_level.strip().upper() if risk_level else DEFAULT_RISK_LEVEL
    arl_rate = ARL_RATES.get(level, ARL_RATES[DEFAULT_RISK_LEVEL])
    return {
        "health_employee": _rate(salary, HEALTH_EMPLOYEE_RATE),
        "health_employer": _rate(salary, HEALTH_EMPLOYER_RATE),
        "pension_employee": _rate(salary, PENSION_EMPLOYEE_RATE),
        "pension_employer": _rate(salary, PENSION_EMPLOYER_RATE),
        "arl_employer": _rate(salary, arl_rate),
        "compensation_fund": _rate(salary, COMPENSATION_FUND_RATE),
        "icbf": _rate(salary, ICBF_RATE),
        "sena": _rate(salary, SENA_RATE),
    }


def compute_severance(salary: Decimal, days_worked: int) -> Decimal:
    """Cesantías: un mes de salario por año trabajado, proporcional (8.33 %)."""
    return round_money(salary * SEVERANCE_ANNUAL_RATE * Decimal(days_worked) / DAYS_PER_MONTH)


def compute_severance_interest(severance: Decimal, days_worked: int) -> Decimal:
    """Intereses sobre cesantías: 1 % mensual proporcional."""
    months = Decimal(days_worked) / DAYS_PER_MONTH
    return round_money(severance * SEVERANCE_INTEREST_MONTHLY_RATE * months)


def compute_vacation(salary: Decimal, days_worked: int) -> Decimal:
    """Prima de vacaciones: 15 días de salario por año, proporcional.

    15 días de sueldo equivalen a medio salario al año: la proporción
    diaria es ``salary * 15 / 360`` y con 360 días da el medio salario
    completo del año.
    """
    return round_money(
        salary
        * Decimal(days_worked)
        * Decimal(VACATION_DAYS_PER_YEAR)
        / (DAYS_PER_MONTH * DAYS_PER_YEAR)
    )


def compute_bonus(salary: Decimal, days_worked: int) -> Decimal:
    """Prima de servicios: 30 días de salario por año, proporcional."""
    return round_money(salary * Decimal(days_worked) / DAYS_PER_YEAR)


__all__ = [
    "ARL_RATES",
    "compute_bonus",
    "compute_contributions",
    "compute_severance",
    "compute_severance_interest",
    "compute_vacation",
    "DEFAULT_RISK_LEVEL",
]
