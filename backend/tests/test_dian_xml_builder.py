"""Tests del generador XML UBL 2.1 DIAN.

Valida contra el XSD oficial de OASIS (UBL 2.1 OS) y contra el subconjunto
local de ``sts:DianExtensions``: el XSD de OASIS ignora las extensiones por
diseño (``ExtensionContent`` procesa ``##other`` con ``lax``).
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from lxml import etree
from sqlalchemy.orm import Session

from app.application.dian.cufe import compute_software_security_code, issue_time_from_datetime
from app.application.dian.xml_builder import (
    CAC_NS,
    CBC_NS,
    STS_NS,
    UBL_INVOICE_NS,
    build_invoice_xml,
)
from tests.dian_factories import make_full_package

SCHEMAS_DIR = Path(__file__).parent.parent / "app" / "application" / "dian" / "schemas"
UBL_XSD = SCHEMAS_DIR / "ubl21" / "maindoc" / "UBL-Invoice-2.1.xsd"
DIAN_XSD = SCHEMAS_DIR / "DIAN-Structures-2-1.xsd"


@pytest.fixture(scope="module")
def ubl_schema() -> etree.XMLSchema:
    return etree.XMLSchema(etree.parse(str(UBL_XSD)))


@pytest.fixture(scope="module")
def dian_schema() -> etree.XMLSchema:
    return etree.XMLSchema(etree.parse(str(DIAN_XSD)))


def _build(db_session: Session) -> tuple[bytes, object]:
    invoice, company, contact, taxes = make_full_package(db_session)
    cufe = "a" * 96
    security_code = compute_software_security_code(
        software_id=company.dian_software_id or "",
        software_pin=company.dian_software_pin,
        invoice_number=invoice.number or "",
    )
    xml = build_invoice_xml(
        invoice=invoice,
        company=company,
        contact=contact,
        taxes=taxes,
        cufe=cufe,
        software_security_code=security_code,
    )
    return xml, invoice


def test_xml_validates_against_official_ubl_xsd(
    db_session: Session,
    ubl_schema: etree.XMLSchema,
    dian_schema: etree.XMLSchema,
) -> None:
    xml, _invoice = _build(db_session)
    document = etree.fromstring(xml)
    assert ubl_schema.validate(document), str(ubl_schema.error_log)

    dian_extensions = document.find(
        f".//{{urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2}}"
        f"ExtensionContent/{{{STS_NS}}}DianExtensions"
    )
    assert dian_extensions is not None
    assert dian_schema.validate(dian_extensions), str(dian_schema.error_log)


def test_namespaces_are_declared(db_session: Session) -> None:
    xml, _invoice = _build(db_session)
    root = etree.fromstring(xml).getroottree().getroot()
    nsmap = root.nsmap
    assert nsmap[None] == UBL_INVOICE_NS
    assert nsmap["cac"] == CAC_NS
    assert nsmap["cbc"] == CBC_NS
    assert nsmap["sts"] == STS_NS
    assert nsmap["ds"] == "http://www.w3.org/2000/09/xmldsig#"
    assert nsmap["xades"] == "http://uri.etsi.org/01903/v1.3.2#"
    assert nsmap["xades141"] == "http://uri.etsi.org/01903/v1.4.1#"


def test_cufe_lives_in_root_uuid_with_scheme_name(db_session: Session) -> None:
    """El CUFE va en cbc:UUID del documento (no dentro de DianExtensions).

    Nota técnica corregida contra el Anexo v1.9: el bloque
    ``sts:DianExtensions`` (a nivel de documento) lleva el control de
    resolución y el SoftwareSecurityCode; el CUFE es ``cbc:UUID`` con
    ``schemeName="CUFE-SHA384"`` inmediatamente después de ``cbc:ID``.
    """
    xml, invoice = _build(db_session)
    root = etree.fromstring(xml)

    uuid_element = root.find(f"{{{CBC_NS}}}UUID")
    assert uuid_element is not None
    assert uuid_element.get("schemeName") == "CUFE-SHA384"
    assert uuid_element.text == "a" * 96

    # El elemento anterior debe ser cbc:ID con el número de la factura.
    previous = uuid_element.getprevious()
    assert previous is not None and previous.tag == f"{{{CBC_NS}}}ID"
    assert previous.text == invoice.number  # type: ignore[attr-defined]

    # Y NO hay ningún cbc:UUID dentro de las extensiones DIAN.
    dian_extensions = root.find(
        f".//{{urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2}}"
        f"ExtensionContent/{{{STS_NS}}}DianExtensions"
    )
    assert dian_extensions is not None
    assert dian_extensions.find(f".//{{{CBC_NS}}}UUID") is None


def test_authorized_invoices_block(db_session: Session) -> None:
    xml, _invoice = _build(db_session)
    root = etree.fromstring(xml)
    authorized = root.find(f".//{{{STS_NS}}}InvoiceControl/{{{STS_NS}}}AuthorizedInvoices")
    assert authorized is not None
    assert authorized.findtext(f"{{{STS_NS}}}Prefix") == "FE"
    assert authorized.findtext(f"{{{STS_NS}}}From") == "1"
    assert authorized.findtext(f"{{{STS_NS}}}To") == "1000"
    assert (
        root.findtext(f".//{{{STS_NS}}}InvoiceControl/{{{STS_NS}}}InvoiceAuthorization")
        == "18764000123456"
    )
    security_code = root.findtext(f".//{{{STS_NS}}}SoftwareSecurityCode")
    assert security_code is not None and len(security_code) == 96


def test_two_lines_and_two_tax_groups(
    db_session: Session,
    ubl_schema: etree.XMLSchema,
) -> None:
    xml, invoice = _build(db_session)
    root = etree.fromstring(xml)

    lines = root.findall(f"{{{CAC_NS}}}InvoiceLine")
    assert len(lines) == len(invoice.lines) == 2  # type: ignore[attr-defined]

    # 2 TaxTotal con TaxSubtotal (19% y 5%) + 1 TaxTotal global sin subtotal.
    tax_totals = root.findall(f"{{{CAC_NS}}}TaxTotal")
    with_subtotals = [
        element for element in tax_totals if element.find(f"{{{CAC_NS}}}TaxSubtotal") is not None
    ]
    assert len(with_subtotals) == 2
    assert len(tax_totals) == 3
    global_total = tax_totals[-1]
    assert global_total.findtext(f"{{{CBC_NS}}}TaxAmount") == "425.00"

    assert ubl_schema.validate(root), str(ubl_schema.error_log)


def test_amounts_use_dot_decimals(db_session: Session) -> None:
    xml, _invoice = _build(db_session)
    text = xml.decode("utf-8")
    assert 'TaxInclusiveAmount currencyID="COP">3325.00<' in text
    assert not re.search(r"\d,\d{2}<", text), "El XML no debe usar coma decimal"


def test_issue_time_uses_colombia_offset(db_session: Session) -> None:
    xml, invoice = _build(db_session)
    issue_time = etree.fromstring(xml).findtext(f"{{{CBC_NS}}}IssueTime")
    # created_at 14:30 UTC → 09:30:00-05:00 en Colombia.
    expected = issue_time_from_datetime(invoice.created_at)  # type: ignore[attr-defined]
    assert issue_time == f"{expected.strftime('%H:%M:%S')}-05:00"


def test_line_with_discount_emits_allowance_charge(
    db_session: Session,
    ubl_schema: etree.XMLSchema,
) -> None:
    xml, _invoice = _build(db_session)
    root = etree.fromstring(xml)
    allowances = root.findall(f"{{{CAC_NS}}}InvoiceLine/{{{CAC_NS}}}AllowanceCharge")
    assert len(allowances) == 1
    assert allowances[0].findtext(f"{{{CBC_NS}}}ChargeIndicator") == "false"
    assert allowances[0].findtext(f"{{{CBC_NS}}}Amount") == "100.00"
    assert ubl_schema.validate(root), str(ubl_schema.error_log)
