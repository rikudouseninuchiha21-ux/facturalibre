"""Liquidación básica de nómina y su integración contable.

REQUIERE VALIDACIÓN: experto en nómina colombiana. Los porcentajes fijos de
salud y pensión, la ausencia de topes (IBC), las exoneraciones, la retención en
la fuente, los parafiscales, las prestaciones sociales y los aportes del
empleador quedan fuera de esta fase y deben implementarse antes de producción.
"""

from __future__ import annotations

import calendar
from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy.orm import Session

from app.application.accounting.service import AccountingService
from app.application.budget_notifications import (
    capture_alert_levels,
    notify_threshold_crossings,
)
from app.application.payroll.payroll_calculator import (
    DEFAULT_RISK_LEVEL,
    compute_bonus,
    compute_contributions,
    compute_severance,
    compute_severance_interest,
    compute_vacation,
)
from app.domain.calculations import round_money
from app.domain.employee_repository import EmployeeRepository
from app.domain.exceptions import PayrollError, ResourceNotFoundError
from app.domain.models.payroll import (
    PayrollContribution,
    PayrollDetail,
    PayrollPeriod,
    PayrollPeriodStatus,
)
from app.domain.payroll_repository import PayrollRepository

HEALTH_RATE = Decimal("0.04")
PENSION_RATE = Decimal("0.04")


class PayrollService:
    """Calcula el detalle de un periodo y genera su asiento contable.

    No hace commit. La API ejecuta ``calculate_period`` dentro de
    ``operation_transaction`` para que el periodo, el detalle y el asiento sean
    atómicos.
    """

    def __init__(self, db: Session) -> None:
        self.db = db
        self.payroll_repository = PayrollRepository(db)
        self.employee_repository = EmployeeRepository(db)

    @staticmethod
    def _days_worked_for(period: PayrollPeriod, employee_start: date) -> int:
        """Días del mes del periodo, recortados por la fecha de ingreso."""
        days_in_month = calendar.monthrange(period.year, period.month)[1]
        month_start = date(period.year, period.month, 1)
        if employee_start > month_start:
            worked = (month_start.replace(day=days_in_month) - employee_start).days + 1
            return max(min(worked, days_in_month), 0)
        return days_in_month

    def calculate_period(self, period_id: UUID) -> PayrollPeriod:
        """Liquida a todos los empleados activos y cierra el periodo.

        Salud y pensión se calculan como 4 % del salario base cada una. Cada
        deducción se redondea con ``ROUND_HALF_UP`` a dos decimales antes de
        restar. El neto se redondea igualmente para persistirse como NUMERIC.
        """
        period = self.payroll_repository.get_for_update(period_id)
        if period is None:
            raise ResourceNotFoundError("Periodo de nómina no encontrado")
        if period.status is PayrollPeriodStatus.CLOSED:
            raise PayrollError("El periodo de nómina ya está cerrado")
        if self.payroll_repository.has_details(period.id):
            raise PayrollError("El periodo de nómina ya tiene una liquidación")

        employees = self.employee_repository.list_active()
        if not employees:
            raise PayrollError("No hay empleados activos para liquidar")

        details: list[PayrollDetail] = []
        contributions: list[PayrollContribution] = []
        for employee in employees:
            base_salary = round_money(employee.base_salary)
            health_deduction = round_money(base_salary * HEALTH_RATE)
            pension_deduction = round_money(base_salary * PENSION_RATE)
            net_pay = round_money(base_salary - health_deduction - pension_deduction)
            detail = PayrollDetail(
                period_id=period.id,
                employee_id=employee.id,
                base_salary=base_salary,
                health_deduction=health_deduction,
                pension_deduction=pension_deduction,
                net_pay=net_pay,
            )
            details.append(detail)

            # Aportes y provisiones de Fase 39A: los aportes del empleado
            # coinciden con las deducciones (misma tasa 4 %), el resto es a
            # cargo del empleador o provisión de prestaciones.
            days_worked = self._days_worked_for(period, employee.start_date)
            rates = compute_contributions(base_salary, employee.risk_level or DEFAULT_RISK_LEVEL)
            severance = compute_severance(base_salary, days_worked)
            contributions.append(
                PayrollContribution(
                    detail=detail,
                    period_id=period.id,
                    health_employee=health_deduction,
                    health_employer=rates["health_employer"],
                    pension_employee=pension_deduction,
                    pension_employer=rates["pension_employer"],
                    arl_employer=rates["arl_employer"],
                    compensation_fund=rates["compensation_fund"],
                    icbf=rates["icbf"],
                    sena=rates["sena"],
                    severance=severance,
                    severance_interest=compute_severance_interest(severance, days_worked),
                    vacation=compute_vacation(base_salary, days_worked),
                    bonus=compute_bonus(base_salary, days_worked),
                )
            )

        self.db.add_all(details)
        self.db.add_all(contributions)
        period.status = PayrollPeriodStatus.CLOSED
        self.db.flush()

        # Snapshot de niveles de alerta antes del asiento: si la nómina cruza
        # un umbral presupuestal del centro en el mes, se notifica in-app en
        # la misma transacción.
        previous_levels = None
        if period.cost_center_id is not None:
            previous_levels = capture_alert_levels(
                self.db,
                cost_center_id=period.cost_center_id,
                entry_date=date(period.year, period.month, 1),
            )

        entry = AccountingService(self.db).record_payroll(period)
        if entry is None:
            raise PayrollError("No se generó el asiento contable de la nómina")

        if previous_levels is not None and period.cost_center_id is not None:
            notify_threshold_crossings(
                self.db,
                previous=previous_levels,
                cost_center_id=period.cost_center_id,
                entry_date=date(period.year, period.month, 1),
            )

        return period
