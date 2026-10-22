"""Cálculos monetarios puros para facturas.

Todas las operaciones usan Decimal. El redondeo se hace por línea y con
ROUND_HALF_UP a dos decimales, antes de sumar los totales de la factura.

REQUIERE VALIDACIÓN: contador/experto DIAN. La política de redondeo por línea,
la base gravable después del descuento y el tratamiento de impuestos deben
confirmarse contra la normativa y el sistema de facturación electrónica.
"""

from collections.abc import Iterable
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

CENT = Decimal("0.01")
ONE_HUNDRED = Decimal("100")
ZERO_MONEY = Decimal("0.00")


@dataclass(frozen=True)
class LineAmounts:
    """Importes calculados de una línea."""

    subtotal: Decimal
    tax: Decimal
    total: Decimal


@dataclass(frozen=True)
class InvoiceAmounts:
    """Totales calculados de una factura."""

    subtotal: Decimal
    tax_total: Decimal
    total: Decimal
    balance: Decimal


def round_money(value: Decimal) -> Decimal:
    """Redondea a dos decimales usando ROUND_HALF_UP."""
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


def calculate_line(
    *,
    quantity: Decimal,
    unit_price: Decimal,
    discount_percent: Decimal,
    tax_rate: Decimal,
) -> LineAmounts:
    """Calcula subtotal, impuesto y total de una línea.

    Fórmulas:
    - subtotal = round(quantity * unit_price * (1 - discount_percent / 100), 2)
    - tax = round(subtotal * tax_rate / 100, 2)
    - total = subtotal + tax
    """
    discount_factor = Decimal("1") - (discount_percent / ONE_HUNDRED)
    subtotal = round_money(quantity * unit_price * discount_factor)
    tax = round_money(subtotal * tax_rate / ONE_HUNDRED)
    total = round_money(subtotal + tax)
    return LineAmounts(subtotal=subtotal, tax=tax, total=total)


def calculate_invoice_totals(lines: Iterable[LineAmounts]) -> InvoiceAmounts:
    """Suma los importes ya redondeados de cada línea."""
    subtotal = ZERO_MONEY
    tax_total = ZERO_MONEY
    total = ZERO_MONEY

    for line in lines:
        subtotal += line.subtotal
        tax_total += line.tax
        total += line.total

    return InvoiceAmounts(
        subtotal=round_money(subtotal),
        tax_total=round_money(tax_total),
        total=round_money(total),
        balance=round_money(total),
    )
