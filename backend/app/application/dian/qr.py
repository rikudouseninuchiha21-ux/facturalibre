"""QR de la factura electrónica (Resolución DIAN 000165/2023).

El QR lleva los 17 campos oficiales como query string plano (los valores
no se codifican porcentualmente; así lo especifica la resolución y el
campo ``URL`` va al final):
``NumFac, FecFac, HorFac, NitOFE, NombreOFE, ValFac, CodImp1, ValImp1,
CodImp2, ValImp2, CodImp3, ValImp3, ValTot, NumAdq, NombreAdq, CUFE, URL``.
"""

from __future__ import annotations

import io
from datetime import time
from decimal import Decimal
from typing import TYPE_CHECKING

import qrcode
from qrcode.image.pil import PilImage

from app.application.dian.cufe import (
    CUFE_TAX_ORDER,
    format_issue_time,
    format_money,
)

if TYPE_CHECKING:
    from app.domain.models.company_setting import CompanySetting
    from app.domain.models.contact import Contact
    from app.domain.models.invoice import Invoice

QR_SEARCH_URL = "https://catalogo-vpfe.dian.gov.co/document/searchqr?documentkey="

QR_FIELDS_ORDER: tuple[str, ...] = (
    "NumFac",
    "FecFac",
    "HorFac",
    "NitOFE",
    "NombreOFE",
    "ValFac",
    "CodImp1",
    "ValImp1",
    "CodImp2",
    "ValImp2",
    "CodImp3",
    "ValImp3",
    "ValTot",
    "NumAdq",
    "NombreAdq",
    "CUFE",
    "URL",
)


def build_qr_payload(
    *,
    invoice: Invoice,
    company: CompanySetting,
    contact: Contact,
    cufe: str,
    tax_amounts: dict[str, Decimal],
    issue_time: time,
) -> str:
    """Query string con los 17 campos del QR, en el orden de la resolución.

    ``tax_amounts`` trae el importe por código DIAN de impuesto
    (01 IVA, 04 INC, 03 ICA); los ausentes van con ``0.00``.
    """
    invoice_number = invoice.number or str(invoice.id)
    fields: dict[str, str] = {
        "NumFac": invoice_number,
        "FecFac": invoice.issue_date.isoformat() if invoice.issue_date else "",
        "HorFac": format_issue_time(issue_time),
        "NitOFE": company.tax_id or "",
        "NombreOFE": company.name,
        "ValFac": format_money(invoice.subtotal),
        "ValTot": format_money(invoice.total),
        "NumAdq": contact.tax_id or "",
        "NombreAdq": contact.name,
        "CUFE": cufe,
        "URL": f"{QR_SEARCH_URL}{cufe}",
    }
    for position, code in enumerate(CUFE_TAX_ORDER, start=1):
        fields[f"CodImp{position}"] = code
        fields[f"ValImp{position}"] = format_money(tax_amounts.get(code, Decimal("0.00")))

    return "&".join(f"{name}={fields[name]}" for name in QR_FIELDS_ORDER)


def build_qr_png(payload: str) -> bytes:
    """PNG del QR (para incrustarlo en el PDF con reportlab)."""
    image: PilImage = qrcode.make(payload, box_size=6, border=2)  # type: ignore[assignment]
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


__all__ = ["QR_FIELDS_ORDER", "QR_SEARCH_URL", "build_qr_payload", "build_qr_png"]
