"""Tests del cálculo del CUFE (SHA-384, Anexo Técnico DIAN v1.9)."""

from __future__ import annotations

import hashlib
from datetime import date, time
from decimal import Decimal

from app.application.dian.cufe import (
    PLACEHOLDER_SOFTWARE_PIN,
    compute_cufe,
    compute_software_security_code,
    cufe_concatenation,
)

# Set de prueba: inputs fijos + concatenación literal replicada aquí para
# auditar el orden exacto. El CUFE esperado es el SHA-384 de esa cadena,
# precomputado y hardcodeado (verificable con: echo -n <cadena> | sha384sum).
VECTOR = {
    "invoice_number": "SETP990001584",
    "issue_date": date(2021, 3, 10),
    "issue_time": time(10, 10, 10),
    "subtotal": Decimal("1500000.00"),
    "tax_lines": [
        ("01", Decimal("285000.00")),
        ("04", Decimal("0.00")),
        ("03", Decimal("0.00")),
    ],
    "total": Decimal("1785000.00"),
    "issuer_nit": "899999031",
    "buyer_document": "800197268",
    "software_pin": "fc8eac422eba16e6523640285d54f33e8cc8efc9a3e008306ea9d533eef30296",
    "environment": "HABILITACION",
}

EXPECTED_CONCATENATION = (
    "SETP990001584"
    "2021-03-10"
    "10:10:10-05:00"
    "1500000.00"
    "01"
    "285000.00"
    "04"
    "0.00"
    "03"
    "0.00"
    "1785000.00"
    "899999031"
    "800197268"
    "fc8eac422eba16e6523640285d54f33e8cc8efc9a3e008306ea9d533eef30296"
    "1"
)

EXPECTED_CUFE = (
    "14938b2939e18912676c9038a0aa6f67d726718f47f75a6b0457bf4f1527b177f"
    "992b84cb4a81bdfd0a5678ee944c70b"
)


def test_cufe_matches_dian_vector() -> None:
    assert cufe_concatenation(**VECTOR) == EXPECTED_CONCATENATION  # type: ignore[arg-type]
    assert compute_cufe(**VECTOR) == EXPECTED_CUFE  # type: ignore[arg-type]
    # Doble verificación con hashlib, independiente del módulo.
    assert hashlib.sha384(EXPECTED_CONCATENATION.encode()).hexdigest() == EXPECTED_CUFE


def test_cufe_is_deterministic() -> None:
    first = compute_cufe(**VECTOR)  # type: ignore[arg-type]
    second = compute_cufe(**VECTOR)  # type: ignore[arg-type]
    assert first == second
    assert len(first) == 96
    assert first == first.lower()


def test_cufe_without_pin_uses_placeholder() -> None:
    without_pin = {**VECTOR, "software_pin": None}
    with_placeholder = {**VECTOR, "software_pin": PLACEHOLDER_SOFTWARE_PIN}

    cufe = compute_cufe(**without_pin)  # type: ignore[arg-type]
    assert cufe == compute_cufe(**with_placeholder)  # type: ignore[arg-type]
    # El CUFE con placeholder difiere del CUFE real (no es válido para DIAN).
    assert cufe != EXPECTED_CUFE


def test_cufe_tax_order_is_vat_inc_ica() -> None:
    # Los impuestos entran desordenados y la concatenación los ordena
    # SIEMPRE como IVA(01), INC(04), ICA(03).
    payload = cufe_concatenation(
        invoice_number="FV1",
        issue_date=date(2026, 1, 1),
        issue_time=time(8, 0, 0),
        subtotal=Decimal("1000.00"),
        tax_lines=[
            ("03", Decimal("3.00")),
            ("01", Decimal("190.00")),
            ("04", Decimal("40.00")),
        ],
        total=Decimal("1233.00"),
        issuer_nit="900123456",
        buyer_document="830020470",
        software_pin="abc",
        environment="PRODUCCION",
    )
    assert payload.startswith("FV12026-01-0108:00:00-05:001000.00")
    assert "01190.000440.00033.00" in payload
    assert payload.endswith("900123456830020470abc2")


def test_software_security_code() -> None:
    code = compute_software_security_code(
        software_id="NEXUS-ERP",
        software_pin="",
        invoice_number="FV00000001",
    )
    assert code == hashlib.sha384(b"NEXUS-ERP00000000FV00000001").hexdigest()
