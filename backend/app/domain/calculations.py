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

from app.domain.models.invoice import PaymentStatus

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
    price_includes_tax: bool = False,
) -> LineAmounts:
    """Calcula subtotal, impuesto y total de una línea.

    Fórmulas:
    - Si price_includes_tax es False (precio base sin IVA):
        - subtotal = round(quantity * unit_price * (1 - discount_percent / 100), 2)
        - tax = round(subtotal * tax_rate / 100, 2)
        - total = subtotal + tax
    - Si price_includes_tax es True (precio ya incluye IVA):
        - discounted_price = unit_price * (1 - discount_percent / 100)
        - base_per_unit = discounted_price / (1 + tax_rate / 100)
        - tax_per_unit = discounted_price - base_per_unit
        - subtotal = round(quantity * base_per_unit, 2)
        - tax = round(quantity * tax_per_unit, 2)
        - total = subtotal + tax
    """
    discount_factor = Decimal("1") - (discount_percent / ONE_HUNDRED)

    if price_includes_tax:
        tax_multiplier = Decimal("1") + (tax_rate / ONE_HUNDRED)
        discounted_price = unit_price * discount_factor
        base_per_unit = discounted_price / tax_multiplier
        tax_per_unit = discounted_price - base_per_unit
        subtotal = round_money(quantity * base_per_unit)
        tax = round_money(quantity * tax_per_unit)
    else:
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


def payment_status_for_balance(*, total: Decimal, balance: Decimal) -> PaymentStatus:
    """Deriva el estado de pago a partir del saldo de la factura."""
    if balance == ZERO_MONEY:
        return PaymentStatus.PAID
    if balance < total:
        return PaymentStatus.PARTIALLY_PAID
    return PaymentStatus.UNPAID
