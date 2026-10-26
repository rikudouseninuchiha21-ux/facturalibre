"""Agrupación de los impuestos de una factura por código DIAN y tarifa."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from app.domain.models.tax import Tax

DEFAULT_TAX_CODE = "01"
DEFAULT_TAX_NAME = "IVA"
ZERO = Decimal("0.00")


@dataclass(frozen=True)
class TaxGroup:
    """Impuesto agregado a nivel de factura (código DIAN + tarifa)."""

    code: str
    name: str
    rate: Decimal
    taxable: Decimal
    tax: Decimal


@dataclass
class _Accumulator:
    name: str
    taxable: Decimal
    tax: Decimal


def build_tax_catalog(taxes: list[Tax]) -> dict[Decimal, tuple[str, str]]:
    """Mapea tarifa → (código DIAN, nombre); la primera coincidencia gana."""
    catalog: dict[Decimal, tuple[str, str]] = {}
    for tax in taxes:
        catalog.setdefault(
            tax.rate,
            (tax.dian_tax_code or DEFAULT_TAX_CODE, tax.dian_tax_name or DEFAULT_TAX_NAME),
        )
    return catalog


def tax_info_for_rate(
    rate: Decimal,
    catalog: dict[Decimal, tuple[str, str]],
) -> tuple[str, str]:
    return catalog.get(rate, (DEFAULT_TAX_CODE, DEFAULT_TAX_NAME))


def group_line_taxes(
    lines,
    catalog: dict[Decimal, tuple[str, str]],
) -> list[TaxGroup]:
    """Agrega las líneas por (código, tarifa) con Decimal.

    ``lines`` son las ``InvoiceLine`` de la factura (con line_subtotal,
    line_tax y tax_rate).
    """
    groups: dict[tuple[str, str], _Accumulator] = {}
    for line in lines:
        code, name = tax_info_for_rate(line.tax_rate, catalog)
        key = (code, f"{line.tax_rate:.2f}")
        accumulator = groups.get(key)
        if accumulator is None:
            accumulator = _Accumulator(name=name, taxable=ZERO, tax=ZERO)
            groups[key] = accumulator
        accumulator.taxable += line.line_subtotal
        accumulator.tax += line.line_tax

    return [
        TaxGroup(
            code=code,
            name=groups[(code, rate_text)].name,
            rate=Decimal(rate_text),
            taxable=groups[(code, rate_text)].taxable,
            tax=groups[(code, rate_text)].tax,
        )
        for code, rate_text in sorted(groups)
    ]


def tax_amounts_by_code(groups: list[TaxGroup]) -> dict[str, Decimal]:
    """Importe total por código DIAN (01 IVA, 04 INC, 03 ICA...)."""
    amounts: dict[str, Decimal] = {}
    for group in groups:
        amounts[group.code] = amounts.get(group.code, ZERO) + group.tax
    return amounts


def ordered_lines(lines: list) -> list:
    """Líneas ordenadas por id para un XML/PDF determinista.

    ``selectinload`` no garantiza el orden de la colección entre cargas; el
    número de línea DIAN debe ser estable entre regeneraciones.
    """
    return sorted(lines, key=lambda line: line.id)


__all__ = [
    "DEFAULT_TAX_CODE",
    "DEFAULT_TAX_NAME",
    "TaxGroup",
    "build_tax_catalog",
    "group_line_taxes",
    "ordered_lines",
    "tax_amounts_by_code",
    "tax_info_for_rate",
]
