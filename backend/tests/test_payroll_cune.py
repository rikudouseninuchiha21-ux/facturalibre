"""Tests del CUNE (Código Único de Nómina Electrónica)."""

from __future__ import annotations

import hashlib
from datetime import date, time
from decimal import Decimal
from typing import Any, TypedDict

from app.application.payroll.cune import (
    PLACEHOLDER_SOFTWARE_PIN,
    compute_cune,
    compute_software_security_code,
    cune_concatenation,
)


class CuneVector(TypedDict):
    document_number: str
    period_date: date
    issue_time: time
    total_devengado: Decimal
    total_deducciones: Decimal
    total_neto: Decimal
    employer_nit: str
    employee_document: str
    software_pin: str | None
    environment: str


VECTOR: CuneVector = {
    "document_number": "NE-2026-10",
    "period_date": date(2026, 10, 31),
    "issue_time": time(0, 0, 0),
    "total_devengado": Decimal("1083333.33"),
    "total_deducciones": Decimal("80000.00"),
    "total_neto": Decimal("920000.00"),
    "employer_nit": "900123456",
    "employee_document": "1032456789",
    "software_pin": "fc8eac422eba16e6523640285d54f33e8",
    "environment": "HABILITACION",
}

EXPECTED_CONCATENATION = (
    "NE-2026-10"
    "2026-10-31"
    "00:00:00-05:00"
    "1083333.33"
    "80000.00"
    "920000.00"
    "900123456"
    "1032456789"
    "fc8eac422eba16e6523640285d54f33e8"
    "1"
)

EXPECTED_CUNE = hashlib.sha384(EXPECTED_CONCATENATION.encode()).hexdigest()


def _cune(overrides: dict[str, Any]) -> str:
    return compute_cune(**{**VECTOR, **overrides})


def test_cune_vector_matches_expected() -> None:
    assert cune_concatenation(**VECTOR) == EXPECTED_CONCATENATION
    assert compute_cune(**VECTOR) == EXPECTED_CUNE
    assert len(EXPECTED_CUNE) == 96


def test_cune_is_deterministic() -> None:
    assert compute_cune(**VECTOR) == compute_cune(**VECTOR)


def test_cune_without_pin_uses_placeholder() -> None:
    without_pin = _cune({"software_pin": None})
    with_placeholder = _cune({"software_pin": PLACEHOLDER_SOFTWARE_PIN})
    assert without_pin == with_placeholder
    assert without_pin != EXPECTED_CUNE


def test_cune_changes_with_environment() -> None:
    assert _cune({"environment": "PRODUCCION"}) != EXPECTED_CUNE


def test_software_security_code() -> None:
    code = compute_software_security_code(
        software_id="NEXUS-ERP",
        software_pin="",
        document_number="NE-2026-10",
    )
    assert code == hashlib.sha384(b"NEXUS-ERP00000000NE-2026-10").hexdigest()
