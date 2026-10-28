"""PDF del comprobante de Nómina Electrónica (reportlab, Fase 39A).

Mismo estilo Black & Gold del comprobante de factura de la Fase 38A: por
empleado, devengados, deducciones, aportes del empleador y neto; CUNE y
las notas legales (Decreto 1601 de 2020 y modo habilitación).
"""

from __future__ import annotations

import io
import uuid
from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.application.dian.cufe import format_money
from app.application.payroll.payroll_calculator import DEFAULT_RISK_LEVEL

if TYPE_CHECKING:
    from app.domain.models.company_setting import CompanySetting
    from app.domain.models.payroll import (
        Employee,
        PayrollContribution,
        PayrollDetail,
        PayrollPeriod,
    )

BLACK = colors.HexColor("#18181B")
GOLD = colors.HexColor("#D97706")
GOLD_LIGHT = colors.HexColor("#FBBF24")
SOFT_BG = colors.HexColor("#FAF9F6")
BORDER = colors.HexColor("#E4E4E7")
GRAY = colors.HexColor("#52525B")

LEGAL_LEGEND = (
    "Documento de nómina electrónica generado conforme al Decreto 1601 de "
    "2020, sin firma electrónica y sin envío a la DIAN (Fase 39A)."
)
HABILITACION_LEGEND = "Nómina electrónica generada en modo habilitación — sin validez fiscal aún."

ZERO = Decimal("0.00")


def _style(name: str, **kwargs: object) -> ParagraphStyle:
    defaults: dict[str, object] = {
        "fontName": "Helvetica",
        "fontSize": 8.5,
        "leading": 11,
        "textColor": BLACK,
    }
    defaults.update(kwargs)
    return ParagraphStyle(name, **defaults)  # type: ignore[arg-type]


ITEM_HEADER = ["Documento", "Empleado", "Salario", "Salud", "Pensión", "Neto"]

TITLE_STYLE = _style("t", fontName="Helvetica-Bold", fontSize=16, textColor=GOLD_LIGHT)
SUBTITLE_STYLE = _style("n", fontSize=8, textColor=colors.HexColor("#A1A1AA"))
COMPANY_STYLE = _style("c", fontName="Helvetica-Bold", fontSize=11, textColor=colors.white)
NIT_STYLE = _style("cn", fontSize=8, textColor=colors.HexColor("#A1A1AA"))
ITEM_STYLE = _style("i", fontSize=7.5)
LEGAL_STYLE = _style("l", fontSize=7.5, textColor=GRAY, leading=10)


def _kv(label: str, value: str | None) -> Paragraph:
    return Paragraph(
        f'<font color="#52525B"><b>{escape(label)}:</b></font> {escape(value or "—")}',
        _style("value"),
    )


def build_payroll_pdf(
    *,
    period: PayrollPeriod,
    company: CompanySetting,
    rows: list[tuple[PayrollDetail, PayrollContribution]],
    employees: dict[uuid.UUID, Employee],
    cune: str,
    generation_date: date,
    environment: str = "HABILITACION",
) -> bytes:
    """Genera el PDF A4 del comprobante consolidado del periodo."""
    document_number = f"NE-{period.year}-{period.month:02d}"
    buffer = io.BytesIO()
    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=1.6 * cm,
        rightMargin=1.6 * cm,
        topMargin=1.4 * cm,
        bottomMargin=1.4 * cm,
        title=f"Nómina electrónica {document_number}",
    )

    story: list[object] = []

    header = Table(
        [
            [
                [
                    Paragraph("NEXUS ERP", TITLE_STYLE),
                    Paragraph(
                        "Comprobante de Nómina Electrónica · Decreto 1601 de 2020",
                        SUBTITLE_STYLE,
                    ),
                ],
                [
                    Paragraph(escape(company.name), COMPANY_STYLE),
                    Paragraph(
                        f"NIT {escape(company.tax_id or '')}-{escape(company.dv or '')}",
                        NIT_STYLE,
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

    info = Table(
        [
            [
                _kv("Periodo", f"{period.month:02d}/{period.year}"),
                _kv("Documento", document_number),
                _kv("Fecha de pago", generation_date.isoformat()),
                _kv("CUNE", f"{cune[:8]}…{cune[-4:]}"),
            ]
        ],
        colWidths=[4.4 * cm, 4.4 * cm, 4.4 * cm, 4.6 * cm],
    )
    info.setStyle(
        TableStyle(
            [
                ("BOX", (0, 0), (-1, -1), 0.7, BORDER),
                ("BACKGROUND", (0, 0), (-1, -1), SOFT_BG),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.append(info)
    story.append(Spacer(1, 10))

    # Liquidación por empleado.
    table_rows: list[list[object]] = [list(ITEM_HEADER)]
    totals = {
        "salary": ZERO,
        "health": ZERO,
        "pension": ZERO,
        "net": ZERO,
        "contributions": ZERO,
    }
    for detail, contribution in rows:
        employee = employees[detail.employee_id]
        totals["salary"] += detail.base_salary
        totals["health"] += detail.health_deduction
        totals["pension"] += detail.pension_deduction
        totals["net"] += detail.net_pay
        totals["contributions"] += contribution.total_employer_contributions
        table_rows.append(
            [
                Paragraph(escape(employee.document), ITEM_STYLE),
                Paragraph(
                    escape(
                        f"{employee.first_name} {employee.last_name} · ARL "
                        f"{employee.risk_level or DEFAULT_RISK_LEVEL}"
                    ),
                    ITEM_STYLE,
                ),
                format_money(detail.base_salary),
                format_money(detail.health_deduction),
                format_money(detail.pension_deduction),
                format_money(detail.net_pay),
            ]
        )
    table_rows.append(
        [
            "TOTALES",
            "",
            format_money(totals["salary"]),
            format_money(totals["health"]),
            format_money(totals["pension"]),
            format_money(totals["net"]),
        ]
    )
    employees_table = Table(
        table_rows,
        colWidths=[2.8 * cm, 5.9 * cm, 2.6 * cm, 2.2 * cm, 2.2 * cm, 2.4 * cm],
        repeatRows=1,
    )
    style_commands: list[tuple[object, ...]] = [
        ("BACKGROUND", (0, 0), (-1, 0), BLACK),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 7.5),
        ("ALIGN", (2, 0), (-1, -1), "RIGHT"),
        ("GRID", (0, 0), (-1, -1), 0.4, BORDER),
        ("LINEBELOW", (0, 0), (-1, 0), 1, GOLD),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]
    last_row = len(table_rows) - 1
    style_commands.append(("BACKGROUND", (0, last_row), (-1, last_row), BLACK))
    style_commands.append(("TEXTCOLOR", (0, last_row), (-1, last_row), GOLD_LIGHT))
    style_commands.append(("FONTNAME", (0, last_row), (-1, last_row), "Helvetica-Bold"))
    employees_table.setStyle(TableStyle(style_commands))
    story.append(employees_table)
    story.append(Spacer(1, 8))

    story.append(
        Paragraph(
            f'<font color="#52525B"><b>Aportes a cargo del empleador (PILA):</b></font> '
            f"{format_money(totals['contributions'])}",
            _style("ap"),
        )
    )
    story.append(Spacer(1, 4))
    story.append(
        Paragraph(
            f'<font color="#52525B"><b>CUNE:</b></font> {escape(cune)}',
            _style("cune", fontName="Courier", fontSize=7),
        )
    )
    story.append(Spacer(1, 10))

    legends = Table(
        [
            [
                [
                    Paragraph(escape(LEGAL_LEGEND), LEGAL_STYLE),
                    Spacer(1, 6),
                    *(
                        [
                            Paragraph(escape(HABILITACION_LEGEND), LEGAL_STYLE),
                            Spacer(1, 6),
                        ]
                        if environment == "HABILITACION"
                        else []
                    ),
                ]
            ]
        ],
        colWidths=[17.8 * cm],
    )
    legends.setStyle(
        TableStyle(
            [
                ("BOX", (0, 0), (-1, -1), 0.7, BORDER),
                ("BACKGROUND", (0, 0), (-1, -1), SOFT_BG),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    story.append(legends)

    document.build(story)
    return buffer.getvalue()


__all__ = ["build_payroll_pdf"]
