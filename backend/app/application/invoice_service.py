"""Casos de uso compartidos de facturación.

Concentra la creación del borrador y los efectos de la emisión (inventario,
COGS y contabilidad) para que la API de facturas, el POS y la conversión de
cotizaciones apliquen exactamente las mismas reglas. Ningún método hace commit:
la capa que invoca controla la transacción.
"""

from __future__ import annotations

from collections.abc import Iterable
from decimal import Decimal

from sqlalchemy.orm import Session

from app.application.accounting.service import AccountingService
from app.application.inventory.service import InventoryService
from app.application.invoice_schemas import InvoiceCreate
from app.domain.calculations import (
    LineAmounts,
    calculate_invoice_totals,
    calculate_line,
    round_money,
)
from app.domain.contact_repository import ContactRepository
from app.domain.exceptions import InvoiceValidationError
from app.domain.invoice_repository import InvoiceRepository, NewInvoiceLine
from app.domain.item_repository import ItemRepository
from app.domain.models.invoice import Invoice
from app.domain.models.stock import StockMovement

ZERO = Decimal("0.00")


def create_invoice_draft(db: Session, payload: InvoiceCreate) -> Invoice:
    """Crea una factura DRAFT calculando sus líneas y totales.

    No aplica idempotencia ni confirma la transacción; esas responsabilidades
    quedan en el endpoint que conoce la ``Idempotency-Key`` de la operación.
    """
    contact = ContactRepository(db).get_by_id(payload.contact_id)
    if contact is None:
        raise InvoiceValidationError("contact_id no existe o está eliminado")

    item_repository = ItemRepository(db)
    calculated_lines: list[LineAmounts] = []
    new_lines: list[NewInvoiceLine] = []

    for line in payload.lines:
        item = item_repository.get_by_id(line.item_id)
        if item is None:
            raise InvoiceValidationError(f"item_id {line.item_id} no existe o está eliminado")

        # REQUIERE VALIDACIÓN: contador/experto DIAN. La tarifa por defecto y el
        # código de impuesto deben alinearse con el catálogo tributario oficial.
        if line.tax_rate is not None:
            tax_rate = line.tax_rate
        elif item.tax is not None and item.tax.deleted_at is None:
            tax_rate = item.tax.rate
        else:
            tax_rate = Decimal("0")

        description = line.description or item.description or item.name
        amounts = calculate_line(
            quantity=line.quantity,
            unit_price=line.unit_price,
            discount_percent=line.discount_percent,
            tax_rate=tax_rate,
            price_includes_tax=item.price_includes_tax,
        )
        calculated_lines.append(amounts)
        new_lines.append(
            NewInvoiceLine(
                item_id=item.id,
                description=description,
                quantity=line.quantity,
                unit_price=line.unit_price,
                discount_percent=line.discount_percent,
                tax_rate=tax_rate,
                subtotal=amounts.subtotal,
                tax=amounts.tax,
                total=amounts.total,
            )
        )

    totals = calculate_invoice_totals(calculated_lines)
    return InvoiceRepository(db).create_draft(
        contact_id=contact.id,
        issue_date=payload.issue_date,
        due_date=payload.due_date,
        currency=payload.currency,
        lines=new_lines,
        subtotal=totals.subtotal,
        tax_total=totals.tax_total,
        total=totals.total,
    )


def apply_invoice_issue_effects(db: Session, invoice: Invoice) -> Decimal:
    """Descuenta inventario, calcula COGS y registra el asiento de emisión.

    La factura debe estar ya emitida y bloqueada por ``InvoiceRepository.issue``.
    Devuelve el costo total reconocido para facilitar pruebas y trazabilidad.
    """
    movements = InventoryService(db).register_invoice_issue(invoice)
    cogs = calculate_cogs(movements)
    AccountingService(db).record_invoice_issued(invoice, cogs=cogs)
    return cogs


def calculate_cogs(movements: Iterable[StockMovement]) -> Decimal:
    """Suma cantidad por costo unitario de las salidas valorizadas.

    Las salidas sin costo conocido (por ejemplo, stock histórico cargado sin
    ``unit_cost``) no inventan un costo: se excluyen y el asiento de COGS se
    omite si el total es cero.
    """
    total = sum(
        (
            movement.quantity * movement.unit_cost
            for movement in movements
            if movement.unit_cost is not None
        ),
        ZERO,
    )
    return round_money(total)
