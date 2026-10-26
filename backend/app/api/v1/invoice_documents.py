"""Descarga local del paquete DIAN (XML/PDF) de una factura emitida.

Todo es generación local: sin firma XAdES y sin envío a la DIAN (Fase 38B).
``GET /xml`` y ``GET /pdf`` persisten CUFE/estado la primera vez (write-on-
read idempotente, determinista por construcción); el resto son de solo
lectura.
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.api.dependencies.auth import get_current_user, require_role
from app.application.dian.service import DianDocumentService
from app.domain.models.auth import UserRole
from app.domain.models.invoice import Invoice
from app.infrastructure.database import get_db
from app.infrastructure.transactions import operation_transaction

router = APIRouter(
    prefix="/invoices",
    tags=["invoices"],
    dependencies=[Depends(get_current_user)],
)

DbSession = Annotated[Session, Depends(get_db)]

# El cajero emite facturas (POS) y debe poder descargar su representación.
DOCUMENT_ROLES = [UserRole.ADMIN, UserRole.ACCOUNTANT, UserRole.CASHIER]
ADMIN_ONLY = [UserRole.ADMIN]


def get_dian_service(db: DbSession) -> DianDocumentService:
    """Construye el servicio de documentos DIAN con la sesión de la petición."""
    return DianDocumentService(db)


DianServiceDep = Annotated[DianDocumentService, Depends(get_dian_service)]


def _attachment_filename(invoice: Invoice, extension: str) -> str:
    """FV- + número completo de la factura (el número ya trae el prefijo)."""
    number = invoice.number or str(invoice.id)
    return f"FV-{number}.{extension}"


@router.get(
    "/{invoice_id}/xml",
    response_class=Response,
    dependencies=[Depends(require_role(DOCUMENT_ROLES))],
)
def download_invoice_xml(
    invoice_id: UUID,
    db: DbSession,
    service: DianServiceDep,
) -> Response:
    """XML UBL 2.1 con extensiones DIAN de la factura emitida."""
    invoice, company, contact, taxes = service.load_context(invoice_id)
    with operation_transaction(db):
        cufe = service.ensure_generated(invoice, company, contact, taxes)
    xml_bytes = service.build_xml(invoice, company, contact, taxes, cufe)
    return Response(
        content=xml_bytes,
        media_type="application/xml",
        headers={
            "Content-Disposition": (
                f'attachment; filename="{_attachment_filename(invoice, "xml")}"'
            )
        },
    )


@router.get(
    "/{invoice_id}/pdf",
    response_class=Response,
    dependencies=[Depends(require_role(DOCUMENT_ROLES))],
)
def download_invoice_pdf(
    invoice_id: UUID,
    db: DbSession,
    service: DianServiceDep,
) -> Response:
    """PDF de representación gráfica con QR (Res. 000165/2023)."""
    invoice, company, contact, taxes = service.load_context(invoice_id)
    with operation_transaction(db):
        cufe = service.ensure_generated(invoice, company, contact, taxes)
    pdf_bytes = service.build_pdf(invoice, company, contact, taxes, cufe)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": (
                f'attachment; filename="{_attachment_filename(invoice, "pdf")}"'
            )
        },
    )


@router.get(
    "/{invoice_id}/dian-preview",
    dependencies=[Depends(require_role(ADMIN_ONLY))],
)
def dian_preview(
    invoice_id: UUID,
    service: DianServiceDep,
) -> dict[str, object]:
    """CUFE + XML como texto para depuración (solo ADMIN, no persiste)."""
    invoice, company, contact, taxes = service.load_context(invoice_id)
    cufe = service.compute_invoice_cufe(invoice, company, contact, taxes)
    xml_bytes = service.build_xml(invoice, company, contact, taxes, cufe)
    return {
        "invoice_id": str(invoice.id),
        "number": invoice.number,
        "cufe": cufe,
        "dian_status": service.dian_status_for(company).value,
        "environment": company.dian_environment,
        "software_pin_active": bool(company.dian_software_pin),
        "xml": xml_bytes.decode("utf-8"),
    }


@router.post(
    "/{invoice_id}/regenerate-cufe",
    dependencies=[Depends(require_role(ADMIN_ONLY))],
)
def regenerate_cufe(
    invoice_id: UUID,
    db: DbSession,
    service: DianServiceDep,
) -> dict[str, object]:
    """Recalcula y persiste el CUFE (p. ej. tras cambiar el PIN)."""
    invoice, company, contact, taxes = service.load_context(invoice_id)
    with operation_transaction(db):
        cufe = service.ensure_generated(invoice, company, contact, taxes)
    return {
        "invoice_id": str(invoice.id),
        "number": invoice.number,
        "cufe": cufe,
        "dian_status": invoice.dian_status.value if invoice.dian_status else None,
    }


__all__ = ["router"]
