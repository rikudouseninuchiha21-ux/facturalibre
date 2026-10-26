"""Tests del PDF de representación gráfica y del QR (Res. 000165/2023)."""

from __future__ import annotations

import io

from pypdf import PdfReader
from sqlalchemy.orm import Session

from app.application.dian.cufe import issue_time_from_datetime
from app.application.dian.pdf_builder import build_invoice_pdf
from app.application.dian.qr import (
    QR_FIELDS_ORDER,
    QR_SEARCH_URL,
    build_qr_payload,
    build_qr_png,
)
from app.application.dian.tax_groups import (
    build_tax_catalog,
    group_line_taxes,
    tax_amounts_by_code,
)
from tests.dian_factories import make_full_package

MAX_PDF_BYTES = 1024 * 1024


def _build_pdf(db_session: Session, cufe: str) -> bytes:
    invoice, company, contact, taxes = make_full_package(db_session)
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


def test_pdf_magic_bytes_and_size(db_session: Session) -> None:
    pdf = _build_pdf(db_session, "b" * 96)
    assert pdf.startswith(b"%PDF")
    assert len(pdf) < MAX_PDF_BYTES


def test_pdf_contains_cufe_and_legends(db_session: Session) -> None:
    cufe = "c0ffee1234" + "9" * 86
    pdf = _build_pdf(db_session, cufe)
    reader = PdfReader(io.BytesIO(pdf))
    text = "\n".join(page.extract_text() or "" for page in reader.pages)

    assert cufe[:8] in text
    assert "Art. 779" in text
    assert "sin validez fiscal" in text
    assert "modo habilitación" in text.lower()


def test_qr_payload_has_seventeen_official_fields(db_session: Session) -> None:
    invoice, company, contact, taxes = make_full_package(db_session)
    groups = group_line_taxes(invoice.lines, build_tax_catalog(taxes))
    cufe = "d" * 96

    payload = build_qr_payload(
        invoice=invoice,
        company=company,
        contact=contact,
        cufe=cufe,
        tax_amounts=tax_amounts_by_code(groups),
        issue_time=issue_time_from_datetime(invoice.created_at),
    )

    fields = [part.split("=")[0] for part in payload.split("&")]
    assert tuple(fields) == QR_FIELDS_ORDER
    assert len(fields) == 17
    assert payload.startswith(f"NumFac={invoice.number}&")
    assert "CodImp1=01" in payload
    assert "ValImp1=425.00" in payload
    assert "CodImp2=04" in payload and "ValImp2=0.00" in payload
    assert "CodImp3=03" in payload and "ValImp3=0.00" in payload
    assert f"CUFE={cufe}" in payload
    assert payload.endswith(f"URL={QR_SEARCH_URL}{cufe}")
    assert f"NombreOFE={company.name}" in payload
    assert f"NombreAdq={contact.name}" in payload


def test_qr_png_bytes(db_session: Session) -> None:
    png = build_qr_png("NumFac=FV1&CUFE=test")
    assert png.startswith(b"\x89PNG")
    assert len(png) > 200
