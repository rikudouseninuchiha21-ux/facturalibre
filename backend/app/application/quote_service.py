"""Servicio de cotizaciones: CRUD y conversión a factura.

El servicio no hace commit. La API controla la transacción vía
``operation_transaction`` para que cotización, factura, stock y contabilidad
se confirmen o reviertan juntos.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any, Literal, cast
from uuid import UUID

from sqlalchemy import update
from sqlalchemy.engine import CursorResult
from sqlalchemy.orm import Session

from app.application.invoice_schemas import (
    InvoiceCreate,
    InvoiceLineCreate,
)
from app.application.invoice_service import apply_invoice_issue_effects
from app.domain.calculations import (
    LineAmounts,
    calculate_invoice_totals,
    calculate_line,
)
from app.domain.contact_repository import ContactRepository
from app.domain.exceptions import QuoteStateError, ResourceNotFoundError
from app.domain.invoice_repository import InvoiceRepository, NewInvoiceLine
from app.domain.item_repository import ItemRepository
from app.domain.models.contact import Contact, ContactType
from app.domain.models.invoice import Invoice
from app.domain.models.quote import Quote, QuoteStatus
from app.domain.quote_repository import NewQuoteLine, QuoteRepository


class QuoteService:
    """Lógica de negocio de cotizaciones."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.quotes = QuoteRepository(db)
        self.invoices = InvoiceRepository(db)
        self.contacts = ContactRepository(db)
        self.items = ItemRepository(db)

    def create_draft(
        self,
        *,
        contact_id: UUID,
        issue_date: date,
        expiry_date: date,
        currency: str,
        lines: list[dict],
    ) -> Quote:
        """Crea una cotización DRAFT calculando montos por línea."""
        contact = self.contacts.get_by_id(contact_id)
        if contact is None:
            raise ResourceNotFoundError("contact_id no existe o está eliminado")

        calculated_lines: list[LineAmounts] = []
        new_lines: list[NewQuoteLine] = []

        for line in lines:
            item = self.items.get_by_id(line["item_id"])
            if item is None:
                raise ResourceNotFoundError(f"item_id {line['item_id']} no existe o está eliminado")

            tax_rate = line.get("tax_rate")
            if tax_rate is not None:
                tax_rate_decimal = Decimal(str(tax_rate))
            elif item.tax is not None and item.tax.deleted_at is None:
                tax_rate_decimal = item.tax.rate
            else:
                tax_rate_decimal = Decimal("0")

            description = line.get("description") or item.description or item.name
            amounts = calculate_line(
                quantity=Decimal(str(line["quantity"])),
                unit_price=Decimal(str(line["unit_price"])),
                discount_percent=Decimal(str(line.get("discount_percent", "0"))),
                tax_rate=tax_rate_decimal,
            )
            calculated_lines.append(amounts)
            new_lines.append(
                NewQuoteLine(
                    item_id=item.id,
                    description=description,
                    quantity=Decimal(str(line["quantity"])),
                    unit_price=Decimal(str(line["unit_price"])),
                    tax_rate=tax_rate_decimal,
                    subtotal=amounts.subtotal,
                    tax=amounts.tax,
                    total=amounts.total,
                )
            )

        totals = calculate_invoice_totals(calculated_lines)
        return self.quotes.create_draft(
            contact_id=contact.id,
            issue_date=issue_date,
            expiry_date=expiry_date,
            currency=currency,
            lines=new_lines,
            subtotal=totals.subtotal,
            tax_total=totals.tax_total,
            total=totals.total,
        )

    def convert_to_invoice(self, quote_id: UUID) -> Invoice:
        """Convierte una cotización ACEPTADA en una factura emitida.

        Flujo atómico (coordinado por la API con ``operation_transaction``):
        1. Valida que la cotización esté en ACCEPTED.
        2. Crea una factura DRAFT con los mismos datos y líneas.
        3. Emite la factura (asigna número, descuenta stock, asiento contable).
        4. Cambia el contacto a CUSTOMER.
        5. Marca la cotización como CONVERTED y vincula la factura.
        """
        quote_result = self.quotes.get_by_id(quote_id)
        if quote_result is None:
            raise ResourceNotFoundError("Cotización no encontrada")
        quote, _contact_name = quote_result
        if quote.converted_invoice_id is not None:
            raise QuoteStateError("La cotización ya fue convertida a factura")
        if quote.status is not QuoteStatus.ACCEPTED:
            raise QuoteStateError("Solo se pueden convertir cotizaciones en estado ACEPTADA")

        # Validar que los campos obligatorios no sean None
        if quote.issue_date is None:
            raise ResourceNotFoundError("issue_date no definida en la cotización")
        if quote.expiry_date is None:
            raise ResourceNotFoundError("expiry_date no definida en la cotización")

        # 1. Construir líneas de factura desde la cotización.
        invoice_lines: list[InvoiceLineCreate] = []
        for line in quote.lines:
            if line.item_id is None:
                raise ResourceNotFoundError(f"item_id no definido para la línea {line.description}")
            invoice_lines.append(
                InvoiceLineCreate(
                    item_id=line.item_id,
                    description=line.description,
                    quantity=line.quantity,
                    unit_price=line.unit_price,
                    discount_percent=Decimal("0"),
                    tax_rate=line.tax_rate,
                )
            )

        invoice_payload = InvoiceCreate(
            contact_id=quote.contact_id,
            issue_date=quote.issue_date,
            due_date=quote.expiry_date,
            currency=cast(Literal["COP"], quote.currency),
            lines=invoice_lines,
        )

        # 2. Crear factura DRAFT (sin idempotencia: operación interna).
        calculated_lines: list[LineAmounts] = []
        new_invoice_lines: list[NewInvoiceLine] = []

        for line_payload in invoice_payload.lines:
            item = self.items.get_by_id(line_payload.item_id)
            if item is None:
                raise ResourceNotFoundError(
                    f"item_id {line_payload.item_id} no existe o está eliminado"
                )

            tax_rate = line_payload.tax_rate
            if tax_rate is not None:
                tax_rate_decimal = tax_rate
            elif item.tax is not None and item.tax.deleted_at is None:
                tax_rate_decimal = item.tax.rate
            else:
                tax_rate_decimal = Decimal("0")

            description = line_payload.description or item.description or item.name
            amounts = calculate_line(
                quantity=line_payload.quantity,
                unit_price=line_payload.unit_price,
                discount_percent=line_payload.discount_percent,
                tax_rate=tax_rate_decimal,
                price_includes_tax=item.price_includes_tax,
            )
            calculated_lines.append(amounts)
            new_invoice_lines.append(
                NewInvoiceLine(
                    item_id=item.id,
                    description=description,
                    quantity=line_payload.quantity,
                    unit_price=line_payload.unit_price,
                    discount_percent=line_payload.discount_percent,
                    tax_rate=tax_rate_decimal,
                    subtotal=amounts.subtotal,
                    tax=amounts.tax,
                    total=amounts.total,
                )
            )

        totals = calculate_invoice_totals(calculated_lines)
        invoice = self.invoices.create_draft(
            contact_id=quote.contact_id,
            issue_date=invoice_payload.issue_date,
            due_date=invoice_payload.due_date,
            currency=invoice_payload.currency,
            lines=new_invoice_lines,
            subtotal=totals.subtotal,
            tax_total=totals.tax_total,
            total=totals.total,
        )

        # 3. Emitir factura (número, stock, COGS y contabilidad) en la misma transacción.
        issued_invoice = self.invoices.issue(invoice.id)
        apply_invoice_issue_effects(self.db, issued_invoice)

        # 4. Cambiar el contacto a CUSTOMER.
        contact = self.contacts.get_by_id(quote.contact_id)
        if contact is not None and contact.type != ContactType.CUSTOMER:
            statement = (
                update(Contact)
                .where(Contact.id == quote.contact_id)
                .values(type=ContactType.CUSTOMER, version=Contact.version + 1)
            )
            result = cast(CursorResult[Any], self.db.execute(statement))
            if result.rowcount == 0:
                raise ResourceNotFoundError("Contacto no encontrado")

        # 5. Marcar cotización como CONVERTED y vincular factura.
        self.quotes.update_status(
            quote_id,
            expected_status=QuoteStatus.ACCEPTED,
            new_status=QuoteStatus.CONVERTED,
        )
        self.quotes.set_converted_invoice(quote_id, issued_invoice.id)

        self.db.flush()
        return issued_invoice
