"""Liquidación básica de nómina y su integración contable.

REQUIERE VALIDACIÓN: experto en nómina colombiana. Los porcentajes fijos de
salud y pensión, la ausencia de topes (IBC), las exoneraciones, la retención en
la fuente, los parafiscales, las prestaciones sociales y los aportes del
empleador quedan fuera de esta fase y deben implementarse antes de producción.
"""

from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from sqlalchemy.orm import Session

from app.application.accounting.service import AccountingService
from app.domain.calculations import round_money
from app.domain.employee_repository import EmployeeRepository
from app.domain.exceptions import PayrollError, ResourceNotFoundError
from app.domain.models.payroll import (
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
        for employee in employees:
            base_salary = round_money(employee.base_salary)
            health_deduction = round_money(base_salary * HEALTH_RATE)
            pension_deduction = round_money(base_salary * PENSION_RATE)
            net_pay = round_money(base_salary - health_deduction - pension_deduction)
            details.append(
                PayrollDetail(
                    period_id=period.id,
                    employee_id=employee.id,
                    base_salary=base_salary,
                    health_deduction=health_deduction,
                    pension_deduction=pension_deduction,
                    net_pay=net_pay,
                )
            )

        self.db.add_all(details)
        period.status = PayrollPeriodStatus.CLOSED
        self.db.flush()

        entry = AccountingService(self.db).record_payroll(period)
        if entry is None:
            raise PayrollError("No se generó el asiento contable de la nómina")

        return period
