"""Fábricas ORM para los tests de documentos DIAN (Fase 38A).

Crea directamente en la sesión un paquete mínimo y válido: empresa con
resolución, adquiriente con datos fiscales, impuestos, ítems y una factura
ISSUED con líneas. Evita pasar por la API (stock/contabilidad) para aislar
la generación de XML/PDF.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.models.company_setting import CompanySetting
from app.domain.models.contact import Contact, ContactStatus, ContactType
from app.domain.models.invoice import Invoice, LifecycleStatus
from app.domain.models.invoice_line import InvoiceLine
from app.domain.models.item import Item
from app.domain.models.tax import Tax

ZERO = Decimal("0.00")


def make_company(
    db: Session,
    *,
    software_pin: str | None = "",
) -> CompanySetting:
    """Empresa con datos DIAN completos, reutilizando la fila del sistema.

    ``company_settings`` es single-row: la migración 0012 siembra una fila
    por defecto ('Mi Empresa S.A.S.', todo NULL). Crear una SEGUNDA fila
    aquí rompía el aislamiento en bases limpias (CI): el repositorio
    ``get()`` veía la fila sembrada vacía y los tests fallaban con 422
    "Datos DIAN incompletos". Como en producción, el factory actualiza la
    fila existente; solo crea una si la base no la tiene.
    """
    company = db.scalar(select(CompanySetting))
    if company is None:
        company = CompanySetting(name="Nexus ERP S.A.S.")
        db.add(company)

    company.name = "Nexus ERP S.A.S."
    company.tax_id = "900123456"
    company.address = "Carrera 15 # 88 - 21"
    company.phone = "+57 300 000 0000"
    company.email = "facturacion@nexus.co"
    company.dv = "8"
    company.tax_regime = "RESPONSABLE_IVA"
    company.person_type = "JURIDICA"
    company.fiscal_responsibility = "O-13"
    company.dian_municipality_code = "11001"
    company.dian_department_code = "11"
    company.country_code = "CO"
    company.dian_resolution_number = "18764000123456"
    company.dian_resolution_prefix = "FE"
    company.dian_resolution_range_from = 1
    company.dian_resolution_range_to = 1000
    company.dian_resolution_valid_from = date(2026, 1, 1)
    company.dian_resolution_valid_to = date(2027, 12, 31)
    company.dian_software_id = "NEXUS-ERP-38A"
    company.dian_software_pin = software_pin
    company.dian_environment = "HABILITACION"
    db.flush()
    return company


def make_contact(db: Session, *, with_dian_data: bool = True) -> Contact:
    contact = Contact(
        name="Comercial Andina Ltda.",
        email="comercial@andina.co",
        tax_id="830020470",
        type=ContactType.CUSTOMER,
        status=ContactStatus.CUSTOMER,
        dv="5" if with_dian_data else None,
        tax_regime="RESPONSABLE_IVA" if with_dian_data else None,
        person_type="JURIDICA" if with_dian_data else None,
        fiscal_responsibility=None,
        dian_municipality_code="05001" if with_dian_data else None,
        dian_department_code="05" if with_dian_data else None,
        country_code="CO",
        address="Calle 100 # 8 - 50" if with_dian_data else None,
    )
    db.add(contact)
    db.flush()
    return contact


def make_taxes(db: Session) -> list[Tax]:
    vat19 = Tax(name="IVA 19%", rate=Decimal("19"), dian_tax_code="01", dian_tax_name="IVA")
    vat5 = Tax(name="IVA 5%", rate=Decimal("5"), dian_tax_code="01", dian_tax_name="IVA")
    db.add_all([vat19, vat5])
    db.flush()
    return [vat19, vat5]


def make_items(db: Session) -> list[Item]:
    consultoria = Item(
        name="Consultoría ERP",
        description="Implementación de módulo",
        unit_price=Decimal("1000.00"),
        dian_code="CONS-001",
        unspsc_code="81112200",
        unit_code="UND",
    )
    bien = Item(
        name="Bien de consumo",
        description="Bien de consumo A",
        unit_price=Decimal("1000.00"),
        dian_code=None,
        unspsc_code=None,
        unit_code=None,
    )
    db.add_all([consultoria, bien])
    db.flush()
    return [consultoria, bien]


def make_issued_invoice(
    db: Session,
    *,
    contact_id: UUID,
    lifecycle_status: LifecycleStatus = LifecycleStatus.ISSUED,
) -> Invoice:
    """Factura con 2 líneas: IVA 19% sin descuento e IVA 5% con 10% de descuento.

    Totales: subtotal 2.900,00 · impuestos 425,00 · total 3.325,00.
    """
    invoice = Invoice(
        number=f"FE{uuid4().int % 10**8:08d}",
        contact_id=contact_id,
        issue_date=date(2026, 10, 25),
        due_date=date(2026, 11, 24),
        lifecycle_status=lifecycle_status,
        subtotal=Decimal("2900.00"),
        tax_total=Decimal("425.00"),
        total=Decimal("3325.00"),
        balance=Decimal("3325.00"),
        currency="COP",
        payment_mean_code="42",
        payment_terms_days=30,
        notes_dian="Observaciones de prueba",
        order_reference="OC-1234",
        created_at=datetime(2026, 10, 25, 14, 30, 0, tzinfo=UTC),
    )
    invoice.lines = [
        InvoiceLine(
            description="Consultoría implementación",
            quantity=Decimal("2"),
            unit_price=Decimal("1000.00"),
            discount_percent=Decimal("0"),
            tax_rate=Decimal("19"),
            line_subtotal=Decimal("2000.00"),
            line_tax=Decimal("380.00"),
            line_total=Decimal("2380.00"),
        ),
        InvoiceLine(
            description="Bien de consumo A",
            quantity=Decimal("1"),
            unit_price=Decimal("1000.00"),
            discount_percent=Decimal("10"),
            tax_rate=Decimal("5"),
            line_subtotal=Decimal("900.00"),
            line_tax=Decimal("45.00"),
            line_total=Decimal("945.00"),
        ),
    ]
    db.add(invoice)
    db.flush()
    return invoice


def make_full_package(
    db: Session,
    *,
    software_pin: str | None = "",
    contact_with_dian_data: bool = True,
) -> tuple[Invoice, CompanySetting, Contact, list[Tax]]:
    """Empresa + adquiriente + impuestos + factura emitida (todo válido)."""
    company = make_company(db, software_pin=software_pin)
    contact = make_contact(db, with_dian_data=contact_with_dian_data)
    taxes = make_taxes(db)
    items = make_items(db)
    invoice = make_issued_invoice(db, contact_id=contact.id)
    invoice.lines[0].item_id = items[0].id
    invoice.lines[1].item_id = items[1].id
    db.flush()
    return invoice, company, contact, taxes


__all__ = [
    "make_company",
    "make_contact",
    "make_full_package",
    "make_issued_invoice",
    "make_items",
    "make_taxes",
]
