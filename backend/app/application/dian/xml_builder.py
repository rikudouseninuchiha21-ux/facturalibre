"""Generador de XML UBL 2.1 con extensiones DIAN (Anexo Técnico v1.9).

Genera el documento SIN FIRMA XAdES y SIN envío a la DIAN (Fase 38B).

Dónde va el CUFE (fuente clásica de rechazo):
    El CUFE vive en ``cbc:UUID`` con ``schemeName="CUFE-SHA384"`` como hijo
    directo del elemento raíz ``Invoice`` (entre ``cbc:ID`` y
    ``cbc:IssueDate``). El bloque ``ext:UBLExtensions/sts:DianExtensions``
    es un hermano ANTERIOR de ``cbc:UBLVersionID`` a nivel de documento —
    NO dentro del supplier party — y lleva el control de resolución,
    el proveedor del software y el ``sts:SoftwareSecurityCode``
    (SHA-384 de SoftwareID + PIN + número de factura).

Validación:
    - El documento completo valida contra el XSD oficial UBL 2.1 de OASIS
      (``schemas/ubl21/maindoc/UBL-Invoice-2.1.xsd``). El contenido de
      ``ext:ExtensionContent`` se procesa con ``lax`` y el namespace DIAN
      no está declarado en el árbol OASIS, así que el bloque DIAN se valida
      aparte contra ``schemas/DIAN-Structures-2-1.xsd`` (subconjunto local
      del Structures-2-1 oficial).

El orden de los elementos sigue exactamente el XSD OASIS (ver tests).
"""

from __future__ import annotations

from datetime import time
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from lxml import etree

from app.application.dian.cufe import (
    format_issue_time,
    format_money,
    issue_time_from_datetime,
)
from app.application.dian.tax_groups import (
    build_tax_catalog,
    group_line_taxes,
    ordered_lines,
    tax_info_for_rate,
)

if TYPE_CHECKING:
    from app.domain.models.company_setting import CompanySetting
    from app.domain.models.contact import Contact
    from app.domain.models.invoice import Invoice
    from app.domain.models.tax import Tax

# -- Namespaces obligatorios del perfil DIAN 2.1 ---------------------------

UBL_INVOICE_NS = "urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"
CAC_NS = "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"
CBC_NS = "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
EXT_NS = "urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2"
STS_NS = "dian:gov:co:facturaelectronica:Structures-2-1"
DS_NS = "http://www.w3.org/2000/09/xmldsig#"
XADES_NS = "http://uri.etsi.org/01903/v1.3.2#"
XADES141_NS = "http://uri.etsi.org/01903/v1.4.1#"

NAMESPACES: dict[str | None, str] = {
    None: UBL_INVOICE_NS,
    "cac": CAC_NS,
    "cbc": CBC_NS,
    "ext": EXT_NS,
    "sts": STS_NS,
    "ds": DS_NS,
    "xades": XADES_NS,
    "xades141": XADES141_NS,
}

CURRENCY = "COP"
COUNTRY_CODE = "CO"
COUNTRY_NAME = "Colombia"
# Medio de pago por defecto cuando la factura no lo declara (históricas).
# "ZZZ" = "Otros" en el catálogo DIAN: no se afirma un medio que no se conoce.
DEFAULT_PAYMENT_MEAN_CODE = "ZZZ"

UBL_VERSION_ID = "UBL 2.1"
CUSTOMIZATION_ID = "10"
PROFILE_ID = "DIAN 2.1: Factura Electrónica de Venta"
INVOICE_TYPE_CODE = "01"
# NIT de la DIAN como autoridad que emite la resolución.
DIAN_AUTHORITY_NIT = "800197268"
DEFAULT_TAX_CODE = "01"
DEFAULT_TAX_NAME = "IVA"
DEFAULT_UNIT_CODE = "UND"
SOFTWARE_ID_FALLBACK = "NEXUS-ERP"


ZERO = Decimal("0.00")


def _q(namespace: str, tag: str) -> str:
    return f"{{{namespace}}}{tag}"


def _sub(parent: Any, namespace: str, tag: str, text: str | None = None, **attrs: str) -> Any:
    """Crea un hijo con texto plano y atributos; devuelve el hijo."""
    element = etree.SubElement(parent, _q(namespace, tag))
    if text is not None:
        element.text = text
    for key, value in attrs.items():
        element.set(key, value)
    return element


def _cbc(parent: Any, tag: str, text: str | None = None, **attrs: str) -> Any:
    return _sub(parent, CBC_NS, tag, text, **attrs)


def _cac(parent: Any, tag: str) -> Any:
    return _sub(parent, CAC_NS, tag)


def _amount(parent: Any, tag: str, value: Decimal) -> Any:
    """Elemento de importe: 2 decimales con punto y currencyID obligatorio."""
    return _cbc(parent, tag, format_money(value), currencyID=CURRENCY)


def _quantity(value: Decimal) -> str:
    """Cantidad con hasta 4 decimales, sin ceros a la derecha."""
    quantized = value.quantize(Decimal("0.0001"))
    text = format(quantized.normalize(), "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text or "0"


def _build_address(
    parent: Any,
    *,
    municipality_code: str,
    department_code: str,
    address: str,
) -> None:
    """PhysicalLocation/Address con códigos DANE y línea de dirección.

    La DB no guarda nombres de municipio/departamento: ``cbc:CityName`` y
    ``cbc:CountrySubentity`` llevan el código DANE como placeholder
    documentado (la validación semántica DIAN de 38B podrá enriquecerlo).
    """
    _cbc(parent, "ID", municipality_code)
    _cbc(parent, "CityName", municipality_code)
    _cbc(parent, "CountrySubentity", department_code)
    _cbc(parent, "CountrySubentityCode", department_code)
    address_line = _cac(parent, "AddressLine")
    _cbc(address_line, "Line", address)
    country = _cac(parent, "Country")
    _cbc(country, "IdentificationCode", COUNTRY_CODE)
    _cbc(country, "Name", COUNTRY_NAME)


def _build_party_tax_scheme(
    parent: Any,
    *,
    registration_name: str,
    document: str,
    fiscal_responsibility: str | None,
    tax_code: str,
    tax_name: str,
) -> None:
    party_tax_scheme = _cac(parent, "PartyTaxScheme")
    _cbc(party_tax_scheme, "RegistrationName", registration_name)
    _cbc(party_tax_scheme, "CompanyID", document, schemeName="NIT")
    if fiscal_responsibility:
        _cbc(party_tax_scheme, "TaxLevelCode", fiscal_responsibility)
    tax_scheme = _cac(party_tax_scheme, "TaxScheme")
    _cbc(tax_scheme, "ID", tax_code)
    _cbc(tax_scheme, "Name", tax_name)


def _build_supplier_party(
    invoice_element: Any,
    *,
    company: CompanySetting,
) -> None:
    supplier = _cac(invoice_element, "AccountingSupplierParty")
    if company.fiscal_responsibility:
        _cbc(supplier, "AdditionalAccountID", company.fiscal_responsibility)

    party = _cac(supplier, "Party")
    nit = f"{company.tax_id}-{company.dv}"
    identification = _cac(party, "PartyIdentification")
    _cbc(identification, "ID", nit, schemeName="NIT")

    physical_location = _cac(party, "PhysicalLocation")
    _build_address(
        _cac(physical_location, "Address"),
        municipality_code=company.dian_municipality_code or "",
        department_code=company.dian_department_code or "",
        address=company.address or "",
    )

    _build_party_tax_scheme(
        party,
        registration_name=company.name,
        document=nit,
        fiscal_responsibility=company.fiscal_responsibility,
        tax_code=DEFAULT_TAX_CODE,
        tax_name=DEFAULT_TAX_NAME,
    )
    legal_entity = _cac(party, "PartyLegalEntity")
    _cbc(legal_entity, "RegistrationName", company.name)
    _cbc(legal_entity, "CompanyID", nit, schemeName="NIT")


def _build_customer_party(
    invoice_element: Any,
    *,
    contact: Contact,
) -> None:
    customer = _cac(invoice_element, "AccountingCustomerParty")
    if contact.fiscal_responsibility:
        _cbc(customer, "AdditionalAccountID", contact.fiscal_responsibility)

    party = _cac(customer, "Party")
    document = f"{contact.tax_id}-{contact.dv}"
    identification = _cac(party, "PartyIdentification")
    _cbc(identification, "ID", document, schemeName="NIT")
    party_name = _cac(party, "PartyName")
    _cbc(party_name, "Name", contact.name)

    physical_location = _cac(party, "PhysicalLocation")
    _build_address(
        _cac(physical_location, "Address"),
        municipality_code=contact.dian_municipality_code or "",
        department_code=contact.dian_department_code or "",
        address=contact.address or "",
    )

    _build_party_tax_scheme(
        party,
        registration_name=contact.name,
        document=document,
        fiscal_responsibility=contact.fiscal_responsibility,
        tax_code=DEFAULT_TAX_CODE,
        tax_name=DEFAULT_TAX_NAME,
    )
    legal_entity = _cac(party, "PartyLegalEntity")
    _cbc(legal_entity, "RegistrationName", contact.name)
    _cbc(legal_entity, "CompanyID", document, schemeName="NIT")


def _build_dian_extensions(
    invoice_element: Any,
    *,
    company: CompanySetting,
    invoice_number: str,
    software_security_code: str,
) -> None:
    """ext:UBLExtensions → ext:ExtensionContent → sts:DianExtensions.

    Va al inicio del documento (hermano de cbc:UBLVersionID), no dentro
    del supplier party: así lo define el Anexo Técnico v1.9.
    """
    extensions = _sub(invoice_element, EXT_NS, "UBLExtensions")
    extension = _sub(extensions, EXT_NS, "UBLExtension")
    content = _sub(extension, EXT_NS, "ExtensionContent")
    dian = _sub(content, STS_NS, "DianExtensions")

    control = _sub(dian, STS_NS, "InvoiceControl")
    _sub(control, STS_NS, "InvoiceAuthorization", company.dian_resolution_number)
    period = _sub(control, STS_NS, "AuthorizationPeriod")
    _cbc(
        period,
        "StartDate",
        company.dian_resolution_valid_from.isoformat()
        if company.dian_resolution_valid_from
        else "",
    )
    _cbc(
        period,
        "EndDate",
        company.dian_resolution_valid_to.isoformat() if company.dian_resolution_valid_to else "",
    )
    authorized = _sub(control, STS_NS, "AuthorizedInvoices")
    _sub(authorized, STS_NS, "Prefix", company.dian_resolution_prefix)
    _sub(authorized, STS_NS, "From", str(company.dian_resolution_range_from))
    _sub(authorized, STS_NS, "To", str(company.dian_resolution_range_to))

    source = _sub(dian, STS_NS, "InvoiceSource")
    _cbc(source, "IdentificationCode", COUNTRY_CODE)

    provider = _sub(dian, STS_NS, "SoftwareProvider")
    _sub(provider, STS_NS, "ProviderID", company.tax_id, schemeName="NIT")
    _sub(provider, STS_NS, "SoftwareID", company.dian_software_id or SOFTWARE_ID_FALLBACK)

    _sub(dian, STS_NS, "SoftwareSecurityCode", software_security_code)

    authorization_provider = _sub(dian, STS_NS, "AuthorizationProvider")
    _sub(
        authorization_provider,
        STS_NS,
        "AuthorizationProviderID",
        DIAN_AUTHORITY_NIT,
        schemeName="NIT",
    )


def _build_tax_category(parent: Any, *, tax_code: str, tax_name: str, percent: Decimal) -> None:
    category = _cac(parent, "TaxCategory")
    _cbc(category, "ID", tax_code)
    _cbc(category, "Name", tax_name)
    _cbc(category, "Percent", format_money(percent))
    scheme = _cac(category, "TaxScheme")
    _cbc(scheme, "ID", tax_code)
    _cbc(scheme, "Name", tax_name)


def _build_line(
    invoice_element: Any,
    *,
    line: Any,
    index: int,
    catalog: dict[Decimal, tuple[str, str]],
) -> None:
    line_element = _cac(invoice_element, "InvoiceLine")
    _cbc(line_element, "ID", str(index))

    unit_code = DEFAULT_UNIT_CODE
    if line.item is not None and line.item.unit_code:
        unit_code = line.item.unit_code
    _cbc(
        line_element,
        "InvoicedQuantity",
        _quantity(line.quantity),
        unitCode=unit_code,
    )
    _amount(line_element, "LineExtensionAmount", line.line_subtotal)

    if line.discount_percent and line.discount_percent > ZERO:
        allowance = _cac(line_element, "AllowanceCharge")
        _cbc(allowance, "ChargeIndicator", "false")
        discount_amount = line.quantity * line.unit_price - line.line_subtotal
        _amount(allowance, "Amount", discount_amount)
        _amount(allowance, "BaseAmount", line.quantity * line.unit_price)

    tax_code, tax_name = tax_info_for_rate(line.tax_rate, catalog)
    line_tax_total = _cac(line_element, "TaxTotal")
    _amount(line_tax_total, "TaxAmount", line.line_tax)
    subtotal = _cac(line_tax_total, "TaxSubtotal")
    _amount(subtotal, "TaxableAmount", line.line_subtotal)
    _amount(subtotal, "TaxAmount", line.line_tax)
    _cbc(subtotal, "Percent", format_money(line.tax_rate))
    _build_tax_category(subtotal, tax_code=tax_code, tax_name=tax_name, percent=line.tax_rate)

    item = _cac(line_element, "Item")
    _cbc(item, "Description", line.description)
    if line.item is not None:
        _cbc(item, "Name", line.item.name)
        item_code = line.item.dian_code or f"IT-{str(line.item.id)[:8].upper()}"
        identification = _cac(item, "StandardItemIdentification")
        _cbc(identification, "ID", item_code)

    price = _cac(line_element, "Price")
    _amount(price, "PriceAmount", line.unit_price)


def build_invoice_xml(
    *,
    invoice: Invoice,
    company: CompanySetting,
    contact: Contact,
    taxes: list[Tax],
    cufe: str,
    software_security_code: str,
    issue_time: time | None = None,
) -> bytes:
    """Serializa la factura como XML UBL 2.1 DIAN (UTF-8, sin firma).

    ``issue_time`` permite fijar la hora para reproducibilidad en tests;
    por defecto usa la hora de ``invoice.created_at`` en UTC-5 (la hora
    de emisión real quedará persistida en 38B con una columna issued_at).
    """
    invoice_number = invoice.number or str(invoice.id)
    catalog = build_tax_catalog(taxes)

    root = etree.Element(_q(UBL_INVOICE_NS, "Invoice"), nsmap=NAMESPACES)

    _build_dian_extensions(
        root,
        company=company,
        invoice_number=invoice_number,
        software_security_code=software_security_code,
    )

    _cbc(root, "UBLVersionID", UBL_VERSION_ID)
    _cbc(root, "CustomizationID", CUSTOMIZATION_ID)
    _cbc(root, "ProfileID", PROFILE_ID)
    _cbc(root, "ID", invoice_number)
    _cbc(root, "UUID", cufe, schemeName="CUFE-SHA384")
    _cbc(root, "IssueDate", invoice.issue_date.isoformat() if invoice.issue_date else "")
    effective_time = issue_time or issue_time_from_datetime(invoice.created_at)
    _cbc(root, "IssueTime", format_issue_time(effective_time))
    if invoice.due_date is not None:
        _cbc(root, "DueDate", invoice.due_date.isoformat())
    _cbc(root, "InvoiceTypeCode", INVOICE_TYPE_CODE)
    if invoice.notes_dian:
        _cbc(root, "Note", invoice.notes_dian)
    _cbc(root, "DocumentCurrencyCode", invoice.currency)
    _cbc(root, "LineCountNumeric", str(len(invoice.lines)))

    if invoice.due_date is not None and invoice.issue_date is not None:
        period = _cac(root, "InvoicePeriod")
        _cbc(period, "StartDate", invoice.issue_date.isoformat())
        _cbc(period, "EndDate", invoice.due_date.isoformat())

    if invoice.order_reference:
        order_reference = _cac(root, "OrderReference")
        _cbc(order_reference, "ID", invoice.order_reference)

    _build_supplier_party(root, company=company)
    _build_customer_party(root, contact=contact)

    payment_means = _cac(root, "PaymentMeans")
    _cbc(
        payment_means,
        "PaymentMeansCode",
        invoice.payment_mean_code or DEFAULT_PAYMENT_MEAN_CODE,
    )
    if invoice.due_date is not None:
        _cbc(payment_means, "PaymentDueDate", invoice.due_date.isoformat())

    # TaxTotal por (código, tarifa) + TaxTotal global (solo TaxAmount).
    for group in group_line_taxes(invoice.lines, catalog):
        tax_total = _cac(root, "TaxTotal")
        _amount(tax_total, "TaxAmount", group.tax)
        subtotal = _cac(tax_total, "TaxSubtotal")
        _amount(subtotal, "TaxableAmount", group.taxable)
        _amount(subtotal, "TaxAmount", group.tax)
        _cbc(subtotal, "Percent", format_money(group.rate))
        _build_tax_category(
            subtotal,
            tax_code=group.code,
            tax_name=group.name,
            percent=group.rate,
        )
    global_tax_total = _cac(root, "TaxTotal")
    _amount(global_tax_total, "TaxAmount", invoice.tax_total)

    monetary = _cac(root, "LegalMonetaryTotal")
    _amount(monetary, "LineExtensionAmount", invoice.subtotal)
    _amount(monetary, "TaxExclusiveAmount", invoice.subtotal)
    _amount(monetary, "TaxInclusiveAmount", invoice.total)
    _amount(monetary, "PayableAmount", invoice.total)

    for index, line in enumerate(ordered_lines(invoice.lines), start=1):
        _build_line(root, line=line, index=index, catalog=catalog)

    return etree.tostring(
        root,
        xml_declaration=True,
        encoding="UTF-8",
        pretty_print=True,
    )


__all__ = ["NAMESPACES", "build_invoice_xml"]
