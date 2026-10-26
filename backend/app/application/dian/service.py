"""Caso de uso del documento electrónico DIAN (XML + PDF + CUFE), 100% local.

Valida que factura, empresa y adquiriente tengan los datos que el Anexo
Técnico v1.9 exige, calcula el CUFE y expone los bytes del XML/PDF. No
firma XAdES ni envía nada a la DIAN (Fase 38B).

El CUFE es determinista: con los mismos datos (incluido el PIN) produce el
mismo hash. La hora de emisión se toma de ``invoices.created_at`` en hora
de Colombia (offset fijo -05:00).
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.application.dian.cufe import (
    ENVIRONMENT_HABILITACION,
    ENVIRONMENT_PRODUCCION,
    compute_cufe,
    compute_software_security_code,
    issue_time_from_datetime,
)
from app.application.dian.nit import NitValidationError, compute_dv
from app.application.dian.pdf_builder import build_invoice_pdf
from app.application.dian.tax_groups import build_tax_catalog, group_line_taxes
from app.application.dian.xml_builder import SOFTWARE_ID_FALLBACK, build_invoice_xml
from app.domain.company_setting_repository import CompanySettingRepository
from app.domain.exceptions import (
    DianStateError,
    DianValidationError,
    ResourceNotFoundError,
)
from app.domain.models.invoice import DianDocumentStatus, Invoice, LifecycleStatus
from app.domain.models.invoice_line import InvoiceLine
from app.domain.models.tax import Tax

if TYPE_CHECKING:
    from app.domain.models.company_setting import CompanySetting
    from app.domain.models.contact import Contact

VALID_ENVIRONMENTS = (ENVIRONMENT_HABILITACION, ENVIRONMENT_PRODUCCION)


class DianDocumentService:
    """Generación local del paquete DIAN de una factura emitida."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.company_repository = CompanySettingRepository(db)

    # -- Carga y validación -------------------------------------------------

    def load_context(self, invoice_id: UUID) -> tuple[Invoice, CompanySetting, Contact, list[Tax]]:
        """Carga factura emitida + empresa + adquiriente + catálogo de impuestos."""
        invoice = self.db.scalar(
            select(Invoice)
            .where(Invoice.id == invoice_id, Invoice.deleted_at.is_(None))
            .options(
                selectinload(Invoice.contact),
                selectinload(Invoice.lines).selectinload(InvoiceLine.item),
            )
        )
        if invoice is None:
            raise ResourceNotFoundError("Factura no encontrada")
        if invoice.lifecycle_status is not LifecycleStatus.ISSUED:
            raise DianStateError("Solo se generan documentos DIAN de facturas emitidas (issued)")

        company = self.company_repository.get()
        if company is None:
            raise DianValidationError(
                "Falta la configuración de la empresa (empresa.nombre) para generar documentos DIAN"
            )
        contact = invoice.contact
        taxes = list(self.db.scalars(select(Tax)).all())

        missing = self.missing_fields(invoice, company, contact)
        if missing:
            raise DianValidationError(
                "Datos DIAN incompletos para generar el documento: " + ", ".join(missing)
            )
        return invoice, company, contact, taxes

    def missing_fields(
        self,
        invoice: Invoice,
        company: CompanySetting,
        contact: Contact,
    ) -> list[str]:
        """Lista de campos faltantes; vacía cuando el documento puede emitirse."""
        missing: list[str] = []

        if company.tax_id is None or not company.tax_id.strip():
            missing.append("empresa.tax_id (NIT)")
        for field, label in (
            ("dv", "empresa.dv"),
            ("person_type", "empresa.person_type"),
            ("tax_regime", "empresa.tax_regime"),
            ("address", "empresa.address"),
            ("dian_municipality_code", "empresa.dian_municipality_code"),
            ("dian_department_code", "empresa.dian_department_code"),
            ("dian_resolution_number", "empresa.dian_resolution_number"),
            ("dian_resolution_prefix", "empresa.dian_resolution_prefix"),
            ("dian_resolution_valid_from", "empresa.dian_resolution_valid_from"),
            ("dian_resolution_valid_to", "empresa.dian_resolution_valid_to"),
        ):
            if not getattr(company, field):
                missing.append(label)
        if company.dian_resolution_range_from is None:
            missing.append("empresa.dian_resolution_range_from")
        if company.dian_resolution_range_to is None:
            missing.append("empresa.dian_resolution_range_to")
        if company.dian_environment not in VALID_ENVIRONMENTS:
            missing.append("empresa.dian_environment (HABILITACION|PRODUCCION)")

        if contact.tax_id is None or not contact.tax_id.strip():
            missing.append("contacto.tax_id")
        for field, label in (
            ("dv", "contacto.dv"),
            ("person_type", "contacto.person_type"),
            ("tax_regime", "contacto.tax_regime"),
            ("address", "contacto.address"),
            ("dian_municipality_code", "contacto.dian_municipality_code"),
            ("dian_department_code", "contacto.dian_department_code"),
        ):
            if not getattr(contact, field):
                missing.append(label)

        if invoice.issue_date is None:
            missing.append("factura.issue_date")
        if invoice.due_date is None:
            missing.append("factura.due_date")
        if not invoice.payment_mean_code:
            missing.append("factura.payment_mean_code")
        return missing

    # -- CUFE -----------------------------------------------------------------

    def compute_invoice_cufe(
        self,
        invoice: Invoice,
        company: CompanySetting,
        contact: Contact,
        taxes: list[Tax],
    ) -> str:
        """CUFE de la factura con los datos actuales (determinista)."""
        groups = group_line_taxes(invoice.lines, build_tax_catalog(taxes))
        return compute_cufe(
            invoice_number=invoice.number or str(invoice.id),
            issue_date=invoice.issue_date,  # type: ignore[arg-type]
            issue_time=issue_time_from_datetime(invoice.created_at),
            subtotal=invoice.subtotal,
            tax_lines=[(group.code, group.tax) for group in groups],
            total=invoice.total,
            issuer_nit=company.tax_id or "",
            buyer_document=contact.tax_id or "",
            software_pin=company.dian_software_pin,
            environment=company.dian_environment,
        )

    def dian_status_for(self, company: CompanySetting) -> DianDocumentStatus:
        """``GENERADO`` con PIN real; ``GENERADO_SIN_PIN`` con el placeholder."""
        if company.dian_software_pin and company.dian_software_pin.strip():
            return DianDocumentStatus.GENERADO
        return DianDocumentStatus.GENERADO_SIN_PIN

    def ensure_generated(
        self,
        invoice: Invoice,
        company: CompanySetting,
        contact: Contact,
        taxes: list[Tax],
    ) -> str:
        """Calcula el CUFE y lo persiste si es la primera vez o cambió.

        Idempotente: regenerar con los mismos datos produce el mismo CUFE
        y no reescribe nada. El llamador controla la transacción.
        """
        cufe = self.compute_invoice_cufe(invoice, company, contact, taxes)
        status = self.dian_status_for(company)
        if invoice.cufe != cufe or invoice.dian_status is not status:
            invoice.cufe = cufe
            invoice.dian_status = status
            invoice.xml_generated_at = datetime.now(UTC)
        self.db.flush()
        return cufe

    # -- Bytes de XML y PDF ---------------------------------------------------

    def build_xml(
        self,
        invoice: Invoice,
        company: CompanySetting,
        contact: Contact,
        taxes: list[Tax],
        cufe: str,
    ) -> bytes:
        """XML UBL 2.1 DIAN de la factura (sin firma)."""
        security_code = compute_software_security_code(
            software_id=company.dian_software_id or SOFTWARE_ID_FALLBACK,
            software_pin=company.dian_software_pin,
            invoice_number=invoice.number or str(invoice.id),
        )
        return build_invoice_xml(
            invoice=invoice,
            company=company,
            contact=contact,
            taxes=taxes,
            cufe=cufe,
            software_security_code=security_code,
        )

    def build_pdf(
        self,
        invoice: Invoice,
        company: CompanySetting,
        contact: Contact,
        taxes: list[Tax],
        cufe: str,
    ) -> bytes:
        """PDF A4 de representación gráfica con QR (Res. 000165/2023)."""
        groups = group_line_taxes(invoice.lines, build_tax_catalog(taxes))
        return build_invoice_pdf(
            invoice=invoice,
            company=company,
            contact=contact,
            cufe=cufe,
            tax_groups=groups,
            issue_time=issue_time_from_datetime(invoice.created_at),
            environment=company.dian_environment,
        )

    # -- Utilidades ------------------------------------------------------------

    def suggest_dv(self, nit: str) -> str:
        """DV calculado con el algoritmo módulo 11 (útil para validar datos)."""
        try:
            return compute_dv(nit)
        except NitValidationError as error:
            raise DianValidationError(str(error)) from error


__all__ = ["DianDocumentService"]
