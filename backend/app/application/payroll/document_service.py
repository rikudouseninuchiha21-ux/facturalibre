"""Caso de uso del documento electrónico de nómina (XML/PDF/PILA/UGPP, local).

Valida que el periodo esté liquidado (CLOSED) y que empresa y empleados
tengan los datos fiscales del Anexo Técnico, calcula el CUNE (determinista:
fecha de pago o fin de mes + hora fija del periodo) y expone los bytes de
los documentos. Sin firma XAdES y sin envío a la DIAN (Fase 39B).
"""

from __future__ import annotations

import calendar
import uuid
from datetime import UTC, date, datetime, time
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.application.payroll.cune import (
    compute_cune,
    compute_software_security_code,
)
from app.application.payroll.pila_builder import build_pila_file
from app.application.payroll.ugpp_report import build_ugpp_report
from app.application.payroll.xml_builder import (
    build_payroll_xml,
    payroll_document_number,
)
from app.domain.company_setting_repository import CompanySettingRepository
from app.domain.exceptions import (
    DianValidationError,
    PayrollError,
    ResourceNotFoundError,
)
from app.domain.models.invoice import DianDocumentStatus
from app.domain.models.payroll import (
    Employee,
    PayrollContribution,
    PayrollDetail,
    PayrollPeriod,
    PayrollPeriodStatus,
)

if TYPE_CHECKING:
    from app.domain.models.company_setting import CompanySetting

ZERO = Decimal("0.00")

# Fila de liquidación: detalle del empleado y sus aportes del periodo.
PayrollRow = tuple["PayrollDetail", "PayrollContribution"]
# Hora de generación determinista del documento de nómina del periodo
# (una liquidación se emite una vez; reproducible entre regeneraciones).
DOCUMENT_HOUR = time(0, 0, 0)


class PayrollDocumentService:
    """Generación local del paquete de nómina electrónica de un periodo."""

    def __init__(self, db: Session) -> None:
        self.db = db

    # -- Carga y validación -------------------------------------------------

    def load_period(
        self,
        period_id: uuid.UUID,
    ) -> tuple[PayrollPeriod, CompanySetting, list[PayrollRow], dict[uuid.UUID, Employee]]:
        """Carga el periodo liquidado con sus aportes y valida los datos."""
        period = self.db.scalar(
            select(PayrollPeriod)
            .where(PayrollPeriod.id == period_id)
            .options(
                selectinload(PayrollPeriod.details).selectinload(PayrollDetail.employee),
                selectinload(PayrollPeriod.details).selectinload(PayrollDetail.contribution),
            )
        )
        if period is None:
            raise ResourceNotFoundError("Periodo de nómina no encontrado")
        if period.status is not PayrollPeriodStatus.CLOSED:
            raise PayrollError(
                "El periodo de nómina debe estar liquidado (CLOSED) para generar documentos"
            )

        company = CompanySettingRepository(self.db).get()
        if company is None:
            raise DianValidationError(
                "Falta la configuración de la empresa para generar la nómina electrónica"
            )

        details: list[PayrollDetail] = period.details
        if not details:
            raise PayrollError("El periodo no tiene liquidación de empleados")

        missing: list[str] = []
        for field, label in (
            ("tax_id", "empresa.tax_id (NIT)"),
            ("dv", "empresa.dv"),
            ("address", "empresa.address"),
            ("dian_municipality_code", "empresa.dian_municipality_code"),
            ("dian_department_code", "empresa.dian_department_code"),
            ("dian_resolution_number", "empresa.dian_resolution_number"),
            ("dian_resolution_prefix", "empresa.dian_resolution_prefix"),
        ):
            if not getattr(company, field):
                missing.append(label)
        if company.dian_resolution_range_from is None:
            missing.append("empresa.dian_resolution_range_from")
        if company.dian_resolution_range_to is None:
            missing.append("empresa.dian_resolution_range_to")

        rows: list[tuple[PayrollDetail, PayrollContribution]] = []
        employees: dict[uuid.UUID, Employee] = {}
        for detail in details:
            employees[detail.employee_id] = detail.employee
            contribution = self.db.scalar(
                select(PayrollContribution).where(
                    PayrollContribution.payroll_detail_id == detail.id
                )
            )
            if contribution is None:
                raise PayrollError(
                    f"El empleado {detail.employee_name} no tiene aportes calculados"
                )
            rows.append((detail, contribution))
            for field, label in (
                ("document_type", f"{detail.employee_name}: tipo de documento"),
                ("address", f"{detail.employee_name}: dirección"),
                ("municipality_code", f"{detail.employee_name}: municipio DANE"),
                ("department_code", f"{detail.employee_name}: departamento DANE"),
                ("eps_code", f"{detail.employee_name}: código EPS"),
                ("afp_code", f"{detail.employee_name}: código AFP"),
                ("arl_code", f"{detail.employee_name}: código ARL"),
                ("compensation_fund_code", f"{detail.employee_name}: caja de compensación"),
            ):
                if not getattr(detail.employee, field):
                    missing.append(label)

        if missing:
            raise DianValidationError(
                "Datos fiscales incompletos para la nómina electrónica: " + ", ".join(missing)
            )
        return period, company, rows, employees

    # -- CUNE ------------------------------------------------------------------

    def generation_date(self, period: PayrollPeriod) -> date:
        """Fecha de pago o último día del mes del periodo (determinista)."""
        if period.payment_date is not None:
            return period.payment_date
        last_day = calendar.monthrange(period.year, period.month)[1]
        return date(period.year, period.month, last_day)

    def compute_period_cune(
        self,
        period: PayrollPeriod,
        company: CompanySetting,
        rows: list[PayrollRow],
        employees: dict[uuid.UUID, Employee],
    ) -> str:
        total_devengado = sum((detail.base_salary for detail, _ in rows), ZERO)
        total_deducciones = sum(
            (detail.health_deduction + detail.pension_deduction for detail, _ in rows),
            ZERO,
        )
        total_neto = sum((detail.net_pay for detail, _ in rows), ZERO)
        employee = employees[rows[0][0].employee_id]
        return compute_cune(
            document_number=payroll_document_number(period),
            period_date=self.generation_date(period),
            issue_time=DOCUMENT_HOUR,
            total_devengado=total_devengado,
            total_deducciones=total_deducciones,
            total_neto=total_neto,
            employer_nit=company.tax_id or "",
            employee_document=employee.document,
            software_pin=company.dian_software_pin,
            environment=company.dian_environment,
        )

    def dian_status_for(self, company: CompanySetting) -> DianDocumentStatus:
        if company.dian_software_pin and company.dian_software_pin.strip():
            return DianDocumentStatus.GENERADO
        return DianDocumentStatus.GENERADO_SIN_PIN

    def ensure_generated(
        self,
        period: PayrollPeriod,
        company: CompanySetting,
        rows: list[PayrollRow],
        employees: dict[uuid.UUID, Employee],
    ) -> str:
        """Calcula el CUNE y lo persiste si cambió (idempotente)."""
        cune = self.compute_period_cune(period, company, rows, employees)
        status = self.dian_status_for(company)
        if period.dian_cune != cune or period.dian_status is not status:
            period.dian_cune = cune
            period.dian_status = status
            period.xml_generated_at = datetime.now(UTC)
        self.db.flush()
        return cune

    # -- Bytes -------------------------------------------------------------------

    def build_xml(
        self,
        period: PayrollPeriod,
        company: CompanySetting,
        rows: list[PayrollRow],
        employees: dict[uuid.UUID, Employee],
        cune: str,
    ) -> bytes:
        security_code = compute_software_security_code(
            software_id=company.dian_software_id or "NEXUS-ERP",
            software_pin=company.dian_software_pin,
            document_number=payroll_document_number(period),
        )
        return build_payroll_xml(
            period=period,
            company=company,
            rows=rows,
            employees=employees,
            cune=cune,
            security_code=security_code,
            generation_date=self.generation_date(period),
            issue_time=DOCUMENT_HOUR,
        )

    def build_pila(
        self,
        period: PayrollPeriod,
        company: CompanySetting,
        rows: list[PayrollRow],
        employees: dict[uuid.UUID, Employee],
    ) -> str:
        return build_pila_file(
            period=period,
            company=company,
            rows=rows,
            employees=employees,
            generated_at=self.generation_date(period),
        )

    def build_ugpp(
        self,
        period: PayrollPeriod,
        rows: list[PayrollRow],
        employees: dict[uuid.UUID, Employee],
    ) -> dict[str, Any]:
        return build_ugpp_report(period=period, rows=rows, employees=employees)


__all__ = ["PayrollDocumentService"]
