"""Cálculo del CUNE (Código Único de Nómina Electrónica), Anexo Técnico DIAN.

El CUNE es el SHA-384 (hex, 96 caracteres, minúsculas) de la concatenación
plana de los campos clave del documento de nómina:

    NumDoc + FecGen + HorGen + ValDevengado + ValDeducciones + ValNeto +
    NitEmpleador + NumDocEmpleado + ClTec + TipoAmbiente

- ``NumDoc``: identificador del documento de nómina (ej. NE-2026-10).
- ``FecGen``/``HorGen``: fecha/hora de generación (``HH:MM:SS-05:00``).
- Importes con 2 decimales y punto, sin separadores.
- ``ClTec``: PIN del software proveedor; si falta se usa el placeholder
  ``00000000`` y el CUNE queda marcado como de prueba
  (``dian_status=GENERADO_SIN_PIN``) hasta la fase de transmisión (39B).
- ``TipoAmbiente``: 1=Habilitación, 2=Producción.

Determinista: mismos inputs → mismo CUNE.
"""

from __future__ import annotations

import hashlib
from datetime import date, time
from decimal import Decimal

PLACEHOLDER_SOFTWARE_PIN = "00000000"

ENVIRONMENT_CODES = {"HABILITACION": "1", "PRODUCCION": "2"}
COLOMBIA_OFFSET = "-05:00"


def format_money(amount: Decimal) -> str:
    """Importe con 2 decimales, punto decimal y sin separadores."""
    return f"{amount:.2f}"


def software_pin_or_placeholder(software_pin: str | None) -> str:
    pin = (software_pin or "").strip()
    return pin if pin else PLACEHOLDER_SOFTWARE_PIN


def cune_concatenation(
    *,
    document_number: str,
    period_date: date,
    issue_time: time,
    total_devengado: Decimal,
    total_deducciones: Decimal,
    total_neto: Decimal,
    employer_nit: str,
    employee_document: str,
    software_pin: str | None,
    environment: str = "HABILITACION",
) -> str:
    """Cadena exacta que se hashea; expuesta para auditarla en tests."""
    environment_code = ENVIRONMENT_CODES.get(environment, "1")
    return (
        document_number
        + period_date.isoformat()
        + f"{issue_time.strftime('%H:%M:%S')}{COLOMBIA_OFFSET}"
        + format_money(total_devengado)
        + format_money(total_deducciones)
        + format_money(total_neto)
        + employer_nit
        + employee_document
        + software_pin_or_placeholder(software_pin)
        + environment_code
    )


def compute_cune(
    *,
    document_number: str,
    period_date: date,
    issue_time: time,
    total_devengado: Decimal,
    total_deducciones: Decimal,
    total_neto: Decimal,
    employer_nit: str,
    employee_document: str,
    software_pin: str | None,
    environment: str = "HABILITACION",
) -> str:
    """SHA-384 hex (96 caracteres) de la concatenación del Anexo Técnico."""
    payload = cune_concatenation(
        document_number=document_number,
        period_date=period_date,
        issue_time=issue_time,
        total_devengado=total_devengado,
        total_deducciones=total_deducciones,
        total_neto=total_neto,
        employer_nit=employer_nit,
        employee_document=employee_document,
        software_pin=software_pin,
        environment=environment,
    )
    return hashlib.sha384(payload.encode("utf-8")).hexdigest()


def compute_software_security_code(
    *,
    software_id: str,
    software_pin: str | None,
    document_number: str,
) -> str:
    """SHA-384 de SoftwareID + PIN + número del documento (sts:SoftwareSecurityCode)."""
    payload = software_id + software_pin_or_placeholder(software_pin) + document_number
    return hashlib.sha384(payload.encode("utf-8")).hexdigest()


__all__ = [
    "PLACEHOLDER_SOFTWARE_PIN",
    "compute_cune",
    "compute_software_security_code",
    "cune_concatenation",
    "format_money",
    "software_pin_or_placeholder",
]
