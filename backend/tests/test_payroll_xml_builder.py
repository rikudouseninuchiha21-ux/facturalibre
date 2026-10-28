"""Tests del generador XML de Nómina Electrónica (XSD OASIS UBL 2.1)."""

from __future__ import annotations

from pathlib import Path

import pytest
from lxml import etree
from sqlalchemy.orm import Session

from app.application.payroll.cune import compute_software_security_code
from app.application.payroll.document_service import PayrollDocumentService
from app.application.payroll.xml_builder import (
    CBC_NS,
    STS_NS,
    build_payroll_xml,
    payroll_document_number,
)
from tests.payroll_dian_factories import make_payroll_package

SCHEMAS_DIR = Path(__file__).parent.parent / "app" / "application" / "dian" / "schemas"
UBL_XSD = SCHEMAS_DIR / "ubl21" / "maindoc" / "UBL-Invoice-2.1.xsd"


@pytest.fixture(scope="module")
def ubl_schema() -> etree.XMLSchema:
    return etree.XMLSchema(etree.parse(str(UBL_XSD)))


def _rows(db_session: Session, package):
    return [(package["detail"], package["contribution"])], {
        package["employee"].id: package["employee"]
    }


def _cune(db_session: Session, package) -> str:
    service = PayrollDocumentService(db_session)
    rows, employees = _rows(db_session, package)
    return service.compute_period_cune(package["period"], package["company"], rows, employees)


def test_payroll_xml_validates_against_official_xsd(
    db_session: Session,
    ubl_schema: etree.XMLSchema,
) -> None:
    package = make_payroll_package(db_session)
    rows, employees = _rows(db_session, package)
    xml = build_payroll_xml(
        period=package["period"],
        company=package["company"],
        rows=rows,
        employees=employees,
        cune=_cune(db_session, package),
        security_code=compute_software_security_code(
            software_id="NEXUS-ERP-38A",
            software_pin="",
            document_number=payroll_document_number(package["period"]),
        ),
        generation_date=package["period"].payment_date,
        issue_time=__import__("datetime").time(0, 0, 0),
    )
    document = etree.fromstring(xml)
    assert ubl_schema.validate(document), str(ubl_schema.error_log)


def test_cune_lives_in_root_uuid_and_namespaces(db_session: Session) -> None:
    package = make_payroll_package(db_session)
    rows, employees = _rows(db_session, package)
    cune = _cune(db_session, package)
    xml = build_payroll_xml(
        period=package["period"],
        company=package["company"],
        rows=rows,
        employees=employees,
        cune=cune,
        security_code="f" * 96,
        generation_date=package["period"].payment_date,
        issue_time=__import__("datetime").time(0, 0, 0),
    )
    root = etree.fromstring(xml)
    nsmap = root.nsmap
    assert nsmap[None] == "urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"
    assert nsmap["sts"] == STS_NS

    uuid_element = root.find(f"{{{CBC_NS}}}UUID")
    assert uuid_element is not None
    assert uuid_element.get("schemeName") == "CUNE-SHA384"
    assert uuid_element.text == cune
    # El CUNE va en el raíz, no dentro de las extensiones DIAN.
    extensions = root.find(
        f".//{{urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2}}"
        f"ExtensionContent/{{{STS_NS}}}DianExtensions"
    )
    assert extensions is not None
    assert extensions.find(f".//{{{CBC_NS}}}UUID") is None


def test_payroll_xml_earnings_deductions_and_contributions(
    db_session: Session,
    ubl_schema: etree.XMLSchema,
) -> None:
    package = make_payroll_package(db_session)
    rows, employees = _rows(db_session, package)
    xml = build_payroll_xml(
        period=package["period"],
        company=package["company"],
        rows=rows,
        employees=employees,
        cune=_cune(db_session, package),
        security_code="f" * 96,
        generation_date=package["period"].payment_date,
        issue_time=__import__("datetime").time(0, 0, 0),
    ).decode("utf-8")

    # Devengados como InvoiceLine (5 conceptos > 0 del empleado).
    assert xml.count("<cac:InvoiceLine>") == 5
    assert "SALARIO · Salario básico" in xml
    assert "CESANTIAS · Cesantías" in xml

    # Deducciones del empleado como AllowanceCharge.
    assert "SALUD · Aporte a salud (empleado)" in xml
    assert "PENSION · Aporte a pensión (empleado)" in xml

    # Aportes del empleador: un TaxScheme por concepto.
    for concept in ("SALUDEMP", "PENSIONEMP", "ARL", "SENA", "ICBF", "CAJA"):
        assert f"<cbc:ID>{concept}</cbc:ID>" in xml, concept

    # Totales: devengado 1.000.000, deducciones 80.000, neto 920.000.
    assert '<cbc:LineExtensionAmount currencyID="COP">1000000.00<' in xml
    assert '<cbc:AllowanceTotalAmount currencyID="COP">80000.00<' in xml
    assert '<cbc:PayableAmount currencyID="COP">920000.00<' in xml

    document = etree.fromstring(xml.encode())
    assert ubl_schema.validate(document), str(ubl_schema.error_log)
