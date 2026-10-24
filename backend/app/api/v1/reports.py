"""Endpoints de exportación de reportes a CSV."""

from __future__ import annotations

import csv
import io
from collections.abc import Iterable
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api.dependencies.auth import get_current_user
from app.domain.models.invoice import LifecycleStatus
from app.domain.reports_repository import (
    InvoiceExportRow,
    PaymentExportRow,
    ReportsRepository,
)
from app.infrastructure.database import get_db

router = APIRouter(
    prefix="/reports",
    tags=["reports"],
    dependencies=[Depends(get_current_user)],
)

DbSession = Annotated[Session, Depends(get_db)]

INVOICE_CSV_FILENAME = "facturas.csv"
PAYMENT_CSV_FILENAME = "pagos.csv"

INVOICE_STATUS_LABELS: dict[LifecycleStatus, str] = {
    LifecycleStatus.DRAFT: "Borrador",
    LifecycleStatus.ISSUED: "Emitida",
    LifecycleStatus.VOID: "Anulada",
}


def get_reports_repository(db: DbSession) -> ReportsRepository:
    """Construye el repositorio de reportes con la sesión de la petición."""
    return ReportsRepository(db)


ReportsRepositoryDep = Annotated[
    ReportsRepository,
    Depends(get_reports_repository),
]


def _format_money(value: Decimal) -> str:
    """Formatea un importe decimal con dos decimales para el CSV."""
    return f"{value:.2f}"


def _csv_stream(fieldnames: list[str], rows: Iterable[dict[str, str]]) -> Iterable[bytes]:
    """Genera el CSV codificado en utf-8-sig (BOM incluido para Excel)."""
    # El BOM de UTF-8 permite que Excel en Windows detecte la codificación.
    yield "\ufeff".encode("utf-8")

    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=fieldnames, lineterminator="\n")
    writer.writeheader()
    yield buffer.getvalue().encode("utf-8")
    buffer.seek(0)
    buffer.truncate(0)

    for row in rows:
        writer.writerow(row)
        yield buffer.getvalue().encode("utf-8")
        buffer.seek(0)
        buffer.truncate(0)


def _invoices_rows(
    invoices: list[InvoiceExportRow],
) -> Iterable[dict[str, str]]:
    for invoice in invoices:
        yield {
            "Número": invoice.number or "—",
            "Fecha Emisión": (invoice.issue_date.isoformat() if invoice.issue_date else ""),
            "Cliente": invoice.contact_name,
            "Subtotal": _format_money(invoice.subtotal),
            "Impuestos": _format_money(invoice.tax_total),
            "Total": _format_money(invoice.total),
            "Estado": INVOICE_STATUS_LABELS[invoice.lifecycle_status],
        }


def _payments_rows(
    payments: list[PaymentExportRow],
) -> Iterable[dict[str, str]]:
    for payment in payments:
        yield {
            "Factura": payment.invoice_number or "—",
            "Fecha Pago": payment.payment_date.isoformat(),
            "Monto": _format_money(payment.amount),
            "Método": payment.method,
        }


@router.get("/invoices.csv")
def export_invoices_csv(
    repository: ReportsRepositoryDep,
) -> StreamingResponse:
    """Exporta las facturas no eliminadas a un archivo CSV."""
    fieldnames = [
        "Número",
        "Fecha Emisión",
        "Cliente",
        "Subtotal",
        "Impuestos",
        "Total",
        "Estado",
    ]
    return StreamingResponse(
        _csv_stream(
            fieldnames,
            _invoices_rows(repository.list_invoices_for_export()),
        ),
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="{INVOICE_CSV_FILENAME}"',
        },
    )


@router.get("/payments.csv")
def export_payments_csv(
    repository: ReportsRepositoryDep,
) -> StreamingResponse:
    """Exporta los pagos recibidos a un archivo CSV."""
    fieldnames = ["Factura", "Fecha Pago", "Monto", "Método"]
    return StreamingResponse(
        _csv_stream(
            fieldnames,
            _payments_rows(repository.list_payments_for_export()),
        ),
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="{PAYMENT_CSV_FILENAME}"',
        },
    )
