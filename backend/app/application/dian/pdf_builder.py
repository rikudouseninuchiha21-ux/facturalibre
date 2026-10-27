"""PDF de representación gráfica de la factura electrónica (Res. 000165/2023).

Librería: **reportlab** (platypus). Decisión documentada: reportlab pesa
~5 MB y no requiere librerías del sistema; weasyprint ofrece maquetación
HTML/CSS pero añade pango/cairo (~50 MB de imagen Docker). Para un
documento fiscal tabular A4, reportlab es suficiente y mantiene la imagen
ligera. Paleta Black & Gold del proyecto.

Incluye: datos del emisor, bloque de resolución DIAN, adquiriente, datos
del documento, tabla de ítems, totales por impuesto, valor en letras,
CUFE, QR con los 17 campos oficiales y las dos leyendas obligatorias
(Art. 779 ET y modo habilitación).
"""

from __future__ import annotations

import io
from datetime import date, time
from typing import TYPE_CHECKING
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    Image,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.application.dian.cufe import format_issue_time, format_money
from app.application.dian.qr import build_qr_payload, build_qr_png
from app.application.dian.tax_groups import TaxGroup, ordered_lines, tax_amounts_by_code
from app.application.dian.words import number_to_words_es_co
from app.application.dian.xml_builder import DEFAULT_PAYMENT_MEAN_CODE

if TYPE_CHECKING:
    from app.domain.models.company_setting import CompanySetting
    from app.domain.models.contact import Contact
    from app.domain.models.invoice import Invoice

BLACK = colors.HexColor("#18181B")
GOLD = colors.HexColor("#D97706")
GOLD_LIGHT = colors.HexColor("#FBBF24")
SOFT_BG = colors.HexColor("#FAF9F6")
BORDER = colors.HexColor("#E4E4E7")
GRAY = colors.HexColor("#52525B")

LEGAL_LEGEND = (
    "Esta factura se asimila en todos sus efectos a una letra de cambio de "
    "conformidad con el Art. 779 del Estatuto Tributario."
)
HABILITACION_LEGEND = "Factura electrónica generada en modo habilitación — sin validez fiscal aún."
LOCAL_NOTE = (
    "Documento generado localmente por Nexus ERP (Fase 38A): sin firma XAdES y sin envío a la DIAN."
)

PAYMENT_MEAN_LABELS: dict[str, str] = {
    "10": "Efectivo",
    "20": "Cheque",
    "42": "Transferencia",
    "48": "Tarjeta crédito",
    "49": "Tarjeta débito",
    "ZZZ": "Otros",
}


def _style(name: str, **kwargs: object) -> ParagraphStyle:
    defaults: dict[str, object] = {
        "fontName": "Helvetica",
        "fontSize": 8.5,
        "leading": 11,
        "textColor": BLACK,
    }
    defaults.update(kwargs)
    return ParagraphStyle(name, **defaults)  # type: ignore[arg-type]


TITLE_STYLE = _style("title", fontName="Helvetica-Bold", fontSize=16, textColor=GOLD_LIGHT)
COMPANY_STYLE = _style("company", fontName="Helvetica-Bold", fontSize=11, textColor=colors.white)
HEADER_NOTE_STYLE = _style("header_note", fontSize=8, textColor=colors.HexColor("#A1A1AA"))
LABEL_STYLE = _style("label", fontName="Helvetica-Bold", fontSize=8, textColor=GRAY, spaceBefore=4)
VALUE_STYLE = _style("value")
ITEM_STYLE = _style("item", fontSize=8)
LEGAL_STYLE = _style("legal", fontSize=7.5, textColor=GRAY, leading=10)


def _kv(label: str, value: str | None) -> Paragraph:
    return Paragraph(
        f'<font color="#52525B"><b>{escape(label)}:</b></font> {escape(value or "—")}',
        VALUE_STYLE,
    )


def _payment_label(code: str | None) -> str:
    if not code:
        return "—"
    return f"{PAYMENT_MEAN_LABELS.get(code, 'Otros')} ({code})"


def build_invoice_pdf(
    *,
    invoice: Invoice,
    company: CompanySetting,
    contact: Contact,
    cufe: str,
    tax_groups: list[TaxGroup],
    issue_time: time,
    environment: str = "HABILITACION",
) -> bytes:
    """Genera el PDF A4 de la factura. No se persiste: bytes on-demand."""
    invoice_number = invoice.number or str(invoice.id)
    issue_date: date = invoice.issue_date  # type: ignore[assignment]
    tax_amounts = tax_amounts_by_code(tax_groups)

    buffer = io.BytesIO()
    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=1.6 * cm,
        rightMargin=1.6 * cm,
        topMargin=1.4 * cm,
        bottomMargin=1.4 * cm,
        title=f"Factura electrónica {invoice_number}",
    )

    story: list[object] = []

    # -- Encabezado negro con acento dorado ---------------------------------
    header = Table(
        [
            [
                [
                    Paragraph("NEXUS ERP", TITLE_STYLE),
                    Paragraph("Factura Electrónica de Venta · UBL 2.1 DIAN", HEADER_NOTE_STYLE),
                ],
                [
                    Paragraph(escape(company.name), COMPANY_STYLE),
                    Paragraph(
                        f"NIT {escape(company.tax_id or '')}-{escape(company.dv or '')}",
                        HEADER_NOTE_STYLE,
                    ),
                ],
            ]
        ],
        colWidths=[8.5 * cm, 9.3 * cm],
    )
    header.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), BLACK),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("LINEBELOW", (0, 0), (-1, -1), 2, GOLD),
            ]
        )
    )
    story.append(header)
    story.append(Spacer(1, 10))

    # -- Emisor y resolución ------------------------------------------------
    issuer_block = [
        Paragraph("EMISOR", LABEL_STYLE),
        _kv("Razón social", company.name),
        _kv("NIT", f"{company.tax_id}-{company.dv}"),
        _kv("Dirección", company.address),
        _kv("Teléfono", company.phone),
        _kv("Email", company.email),
        _kv("Régimen", company.tax_regime),
        _kv("Responsabilidad fiscal", company.fiscal_responsibility),
        _kv(
            "Municipio / Departamento",
            f"{company.dian_municipality_code} / {company.dian_department_code}",
        ),
    ]
    resolution_block = [
        Paragraph("RESOLUCIÓN DIAN", LABEL_STYLE),
        _kv("Número", company.dian_resolution_number),
        _kv("Prefijo", company.dian_resolution_prefix),
        _kv(
            "Rango autorizado",
            f"{company.dian_resolution_range_from} – {company.dian_resolution_range_to}",
        ),
        _kv(
            "Vigencia",
            f"{company.dian_resolution_valid_from} a {company.dian_resolution_valid_to}",
        ),
        _kv("Ambiente", environment),
    ]
    identity = Table(
        [[issuer_block, resolution_block]],
        colWidths=[9.4 * cm, 8.4 * cm],
    )
    identity.setStyle(
        TableStyle(
            [
                ("BOX", (0, 0), (-1, -1), 0.7, BORDER),
                ("BACKGROUND", (0, 0), (0, 0), SOFT_BG),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.append(identity)
    story.append(Spacer(1, 10))

    # -- Adquiriente y datos del documento ----------------------------------
    terms_days = invoice.payment_terms_days
    if terms_days is None and invoice.due_date is not None:
        terms_days = (invoice.due_date - issue_date).days
    payment_mean_code = invoice.payment_mean_code or DEFAULT_PAYMENT_MEAN_CODE
    buyer_block = [
        Paragraph("ADQUIRENTE", LABEL_STYLE),
        _kv("Nombre / Razón social", contact.name),
        _kv("Documento", f"{contact.tax_id}-{contact.dv}"),
        _kv("Dirección", contact.address),
        _kv("Régimen", contact.tax_regime),
        _kv(
            "Municipio / Departamento",
            f"{contact.dian_municipality_code} / {contact.dian_department_code}",
        ),
    ]
    document_block = [
        Paragraph("DOCUMENTO", LABEL_STYLE),
        _kv("Número", invoice_number),
        _kv(
            "Fecha y hora de emisión",
            f"{issue_date.isoformat()} {format_issue_time(issue_time)}",
        ),
        _kv("Vencimiento", invoice.due_date.isoformat() if invoice.due_date else None),
        _kv("Forma de pago", _payment_label(payment_mean_code)),
        _kv("Plazo", f"{terms_days} días" if terms_days is not None else None),
    ]
    parties = Table([[buyer_block, document_block]], colWidths=[9.4 * cm, 8.4 * cm])
    parties.setStyle(
        TableStyle(
            [
                ("BOX", (0, 0), (-1, -1), 0.7, BORDER),
                ("BACKGROUND", (1, 0), (1, 0), SOFT_BG),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.append(parties)
    story.append(Spacer(1, 10))

    # -- Tabla de ítems ------------------------------------------------------
    item_header = [
        "Código",
        "Descripción",
        "Cant.",
        "Und.",
        "Vlr. unitario",
        "Desc. %",
        "Subtotal",
        "Impuesto",
        "Total",
    ]
    item_rows: list[list[object]] = [list(item_header)]
    for line in ordered_lines(invoice.lines):
        item_code = "—"
        if line.item is not None:
            item_code = line.item.dian_code or f"IT-{str(line.item.id)[:8].upper()}"
        item_rows.append(
            [
                Paragraph(escape(item_code), ITEM_STYLE),
                Paragraph(escape(line.description), ITEM_STYLE),
                format_money(line.quantity),
                line.item.unit_code if line.item is not None and line.item.unit_code else "UND",
                format_money(line.unit_price),
                format_money(line.discount_percent),
                format_money(line.line_subtotal),
                format_money(line.line_tax),
                format_money(line.line_total),
            ]
        )
    items_table = Table(
        item_rows,
        colWidths=[
            2.1 * cm,
            4.6 * cm,
            1.4 * cm,
            1.2 * cm,
            2.1 * cm,
            1.4 * cm,
            2.1 * cm,
            1.9 * cm,
            2.1 * cm,
        ],
        repeatRows=1,
    )
    items_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), BLACK),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 7.5),
                ("ALIGN", (2, 0), (-1, -1), "RIGHT"),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("GRID", (0, 0), (-1, -1), 0.4, BORDER),
                ("LINEBELOW", (0, 0), (-1, 0), 1, GOLD),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, SOFT_BG]),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    story.append(items_table)
    story.append(Spacer(1, 10))

    # -- Totales --------------------------------------------------------------
    totals_rows: list[list[object]] = [["Subtotal", format_money(invoice.subtotal)]]
    for group in tax_groups:
        totals_rows.append([f"{group.name} {format_money(group.rate)}%", format_money(group.tax)])
    totals_rows.append(["TOTAL A PAGAR", format_money(invoice.total)])
    totals_table = Table(
        [
            [Paragraph(str(label), ITEM_STYLE), Paragraph(str(value), ITEM_STYLE)]
            for label, value in totals_rows
        ],
        colWidths=[5.4 * cm, 3.6 * cm],
        hAlign="RIGHT",
    )
    totals_style: list[tuple[object, ...]] = [
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("GRID", (0, 0), (-1, -2), 0.4, BORDER),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ]
    totals_style.append(
        ("BACKGROUND", (0, len(totals_rows) - 1), (-1, len(totals_rows) - 1), BLACK)
    )
    totals_style.append(
        ("TEXTCOLOR", (0, len(totals_rows) - 1), (-1, len(totals_rows) - 1), GOLD_LIGHT)
    )
    totals_style.append(
        (
            "FONTNAME",
            (0, len(totals_rows) - 1),
            (-1, len(totals_rows) - 1),
            "Helvetica-Bold",
        )
    )
    totals_table.setStyle(TableStyle(totals_style))
    story.append(totals_table)
    story.append(Spacer(1, 8))

    # -- Valor en letras + CUFE ----------------------------------------------
    story.append(
        Paragraph(
            f'<font color="#52525B"><b>Valor en letras:</b></font> '
            f"{escape(number_to_words_es_co(invoice.total))}",
            VALUE_STYLE,
        )
    )
    story.append(Spacer(1, 4))
    visible_cufe = f"{cufe[:8]}…{cufe[-4:]}" if len(cufe) > 16 else cufe
    story.append(
        Paragraph(
            f'<font color="#52525B"><b>CUFE:</b></font> {escape(visible_cufe)} '
            '<font color="#A1A1AA">(completo en el código QR)</font>',
            VALUE_STYLE,
        )
    )
    story.append(Spacer(1, 10))

    # -- QR + leyendas --------------------------------------------------------
    payload = build_qr_payload(
        invoice=invoice,
        company=company,
        contact=contact,
        cufe=cufe,
        tax_amounts=tax_amounts,
        issue_time=issue_time,
    )
    qr_image = Image(io.BytesIO(build_qr_png(payload)), width=3.4 * cm, height=3.4 * cm)
    legends = [
        Paragraph(escape(LEGAL_LEGEND), LEGAL_STYLE),
        Spacer(1, 6),
    ]
    if environment == "HABILITACION":
        legends.append(Paragraph(escape(HABILITACION_LEGEND), LEGAL_STYLE))
        legends.append(Spacer(1, 6))
    legends.append(Paragraph(escape(LOCAL_NOTE), LEGAL_STYLE))

    footer = Table([[qr_image, legends]], colWidths=[4 * cm, 13.8 * cm])
    footer.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BOX", (0, 0), (-1, -1), 0.7, BORDER),
                ("BACKGROUND", (0, 0), (-1, -1), SOFT_BG),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    story.append(footer)

    document.build(story)
    return buffer.getvalue()


__all__ = ["build_invoice_pdf"]
