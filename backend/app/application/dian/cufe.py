"""Cálculo del CUFE (Código Único de Factura Electrónica) según el Anexo Técnico DIAN.

El CUFE es el SHA-384 (hex, minúsculas, 96 caracteres) de la concatenación
plana —sin separadores— de:

    NumFac + FecFac + HorFac + ValFac +
    CodImp1 + ValImp1 + CodImp2 + ValImp2 + CodImp3 + ValImp3 +
    ValTot + NitOFE + NumAdq + ClTec + TipoAmb

- ``FecFac``: ``YYYY-MM-DD``; ``HorFac``: ``HH:MM:SS-05:00`` (Colombia no
  tiene horario de verano, el offset fijo -05:00 es determinista).
- ``ValFac``: subtotal (base gravable) con 2 decimales y punto decimal.
- Impuestos del nivel de factura, SIEMPRE los tres pares en el orden
  IVA(01), INC(04), ICA(03); el que falta aporta su código con ``0.00``
  (así lo define el formato del QR en la Resolución 000165/2023).
  Retenciones (05/06/07) y bolsas (22) no entran al CUFE.
- ``ValTot``: total a pagar con 2 decimales.
- ``NitOFE``: NIT del emisor sin DV; ``NumAdq``: documento del adquiriente.
- ``ClTec``: PIN del software proveedor (``dian_software_pin``). Si está
  vacío se usa el placeholder ``00000000`` y el resultado NO es válido para
  la DIAN: el llamador debe marcar el documento como ``GENERADO_SIN_PIN``.
- ``TipoAmb``: 1=Habilitación, 2=Producción.
"""

from __future__ import annotations

import hashlib
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal

PLACEHOLDER_SOFTWARE_PIN = "00000000"

VAT_CODE = "01"  # IVA
INC_CODE = "04"  # Impuesto al consumo
ICA_CODE = "03"  # Impuesto de industria y comercio

ZERO = Decimal("0.00")

# Códigos de impuesto del CUFE en el orden oficial (IVA, INC, ICA).
CUFE_TAX_ORDER: tuple[str, ...] = (VAT_CODE, INC_CODE, ICA_CODE)

ENVIRONMENT_HABILITACION = "HABILITACION"
ENVIRONMENT_PRODUCCION = "PRODUCCION"
ENVIRONMENT_CODES = {ENVIRONMENT_HABILITACION: "1", ENVIRONMENT_PRODUCCION: "2"}

COLOMBIA_OFFSET = "-05:00"


def format_money(amount: Decimal) -> str:
    """Importe con exactamente 2 decimales y punto decimal, sin separadores."""
    return f"{amount:.2f}"


def issue_time_from_datetime(value: datetime) -> time:
    """Hora de un timestamp (UTC o naive) convertida a la hora de Colombia.

    La hora de emisión de la factura se toma de ``invoices.created_at`` (ver
    ``xml_builder``): Colombia no tiene horario de verano, así que el offset
    fijo de -05:00 es determinista y reproducible entre regeneraciones.
    """
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return (value - timedelta(hours=5)).time()


def format_issue_time(issue_time: time) -> str:
    """HorFac en formato HH:MM:SS-05:00 (offset fijo de Colombia)."""
    return f"{issue_time.strftime('%H:%M:%S')}{COLOMBIA_OFFSET}"


def normalize_environment(environment: str) -> str:
    """Código numérico del ambiente DIAN; HABILITACION por defecto."""
    return ENVIRONMENT_CODES.get(environment, "1")


def software_pin_or_placeholder(software_pin: str | None) -> str:
    """ClTec real o el placeholder ``00000000`` (CUFE de prueba)."""
    pin = (software_pin or "").strip()
    return pin if pin else PLACEHOLDER_SOFTWARE_PIN


def _cufe_taxes(tax_lines: list[tuple[str, Decimal]]) -> dict[str, Decimal]:
    """Suma los importes por código DIAN, limitado a IVA/INC/ICA."""
    totals = {code: ZERO for code in CUFE_TAX_ORDER}
    for code, amount in tax_lines:
        if code in totals:
            totals[code] += amount
    return totals


def cufe_concatenation(
    *,
    invoice_number: str,
    issue_date: date,
    issue_time: time,
    subtotal: Decimal,
    tax_lines: list[tuple[str, Decimal]],
    total: Decimal,
    issuer_nit: str,
    buyer_document: str,
    software_pin: str | None,
    environment: str,
) -> str:
    """Cadena exacta que la DIAN hashea para obtener el CUFE.

    Expuesta aparte para poder auditar el orden de concatenación en tests.
    """
    taxes = _cufe_taxes(tax_lines)
    tax_part = "".join(code + format_money(taxes[code]) for code in CUFE_TAX_ORDER)
    return (
        invoice_number
        + issue_date.isoformat()
        + format_issue_time(issue_time)
        + format_money(subtotal)
        + tax_part
        + format_money(total)
        + issuer_nit
        + buyer_document
        + software_pin_or_placeholder(software_pin)
        + normalize_environment(environment)
    )


def compute_cufe(
    *,
    invoice_number: str,
    issue_date: date,
    issue_time: time,
    subtotal: Decimal,
    tax_lines: list[tuple[str, Decimal]],
    total: Decimal,
    issuer_nit: str,
    buyer_document: str,
    software_pin: str | None,
    environment: str,
) -> str:
    """SHA-384 hex (96 caracteres, minúsculas) de la concatenación DIAN.

    Determinista: mismos inputs → mismo CUFE. Con ``software_pin`` vacío
    usa el placeholder ``00000000`` y el CUFE queda marcado como de
    prueba (el llamador debe fijar ``dian_status=GENERADO_SIN_PIN``).
    """
    payload = cufe_concatenation(
        invoice_number=invoice_number,
        issue_date=issue_date,
        issue_time=issue_time,
        subtotal=subtotal,
        tax_lines=tax_lines,
        total=total,
        issuer_nit=issuer_nit,
        buyer_document=buyer_document,
        software_pin=software_pin,
        environment=environment,
    )
    return hashlib.sha384(payload.encode("utf-8")).hexdigest()


def compute_software_security_code(
    *,
    software_id: str,
    software_pin: str | None,
    invoice_number: str,
) -> str:
    """SHA-384 de SoftwareID + PIN + número de factura (sts:SoftwareSecurityCode)."""
    payload = software_id + software_pin_or_placeholder(software_pin) + invoice_number
    return hashlib.sha384(payload.encode("utf-8")).hexdigest()


__all__ = [
    "CUFE_TAX_ORDER",
    "ENVIRONMENT_CODES",
    "ENVIRONMENT_HABILITACION",
    "ENVIRONMENT_PRODUCCION",
    "ICA_CODE",
    "INC_CODE",
    "PLACEHOLDER_SOFTWARE_PIN",
    "VAT_CODE",
    "compute_cufe",
    "compute_software_security_code",
    "cufe_concatenation",
    "format_issue_time",
    "issue_time_from_datetime",
    "format_money",
    "software_pin_or_placeholder",
]
