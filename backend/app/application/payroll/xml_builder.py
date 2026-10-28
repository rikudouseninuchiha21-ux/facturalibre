"""Generador XML UBL 2.1 de Nómina Electrónica (Decreto 1601 de 2020, Fase 39A).

Genera el documento consolidado del periodo (un CUNE por periodo, como
modeló la migración 0027) SIN firma XAdES y SIN envío a la DIAN (39B).

Decisión documentada — ``cac:PayrollLine`` no existe en UBL 2.1: emitirlo
rompería la validación contra el XSD oficial. Los devengados se emiten
como ``cac:InvoiceLine`` (una por concepto de cada empleado) y las
deducciones como ``cac:AllowanceCharge`` a nivel de documento, que son los
equivalentes UBL válidos. Los aportes del empleador van en ``cac:TaxTotal``
con un ``cac:TaxScheme`` por concepto (SALUD, PENSIÓN, ARL, SENA, ICBF,
CAJA).

Validación: mismo perfil UBL que la factura → valida contra el XSD oficial
OASIS UBL 2.1 OS ya commiteado en ``app/application/dian/schemas/``. El
XSD específico de la extensión DIAN de nómina no se publica en una URL
estable (se distribuye en el ZIP del Anexo Técnico); se integra en 39B.
"""

from __future__ import annotations

import uuid
from datetime import date, time
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from lxml import etree

from app.application.dian.cufe import format_money
from app.application.dian.xml_builder import (
    CAC_NS,
    CBC_NS,
    COUNTRY_CODE,
    COUNTRY_NAME,
    DIAN_AUTHORITY_NIT,
    EXT_NS,
    NAMESPACES,
    SOFTWARE_ID_FALLBACK,
    STS_NS,
    UBL_INVOICE_NS,
)

if TYPE_CHECKING:
    from app.domain.models.company_setting import CompanySetting
    from app.domain.models.payroll import (
        Employee,
        PayrollContribution,
        PayrollDetail,
        PayrollPeriod,
    )

CURRENCY = "COP"
UBL_VERSION_ID = "UBL 2.1"
CUSTOMIZATION_ID = "10"
PROFILE_ID = "DIAN 2.1: Nómina Electrónica"
INVOICE_TYPE_CODE = "NOM"
ZERO = Decimal("0.00")

# Conceptos DIAN de devengado (base gravable) emitidos como InvoiceLine.
EARNED_CONCEPTS: tuple[tuple[str, str], ...] = (
    ("SALARIO", "Salario básico"),
    ("CESANTIAS", "Cesantías"),
    ("INTCESANTIAS", "Intereses sobre cesantías"),
    ("VACACIONES", "Prima de vacaciones"),
    ("PRIMA", "Prima de servicios"),
)

# Deducciones del empleado (AllowanceCharge) y aportes del empleador
# (TaxTotal con TaxScheme por concepto).
DEDUCTION_CONCEPTS: tuple[tuple[str, str], ...] = (
    ("SALUD", "Aporte a salud (empleado)"),
    ("PENSION", "Aporte a pensión (empleado)"),
)

EMPLOYER_CONTRIBUTION_CONCEPTS: tuple[tuple[str, str, str], ...] = (
    ("SALUDEMP", "Aporte a salud (empleador)", "health_employer"),
    ("PENSIONEMP", "Aporte a pensión (empleador)", "pension_employer"),
    ("ARL", "Aporte a ARL", "arl_employer"),
    ("SENA", "Aporte al SENA", "sena"),
    ("ICBF", "Aporte al ICBF", "icbf"),
    ("CAJA", "Aporte a caja de compensación", "compensation_fund"),
)


def _sub(parent: Any, namespace: str, tag: str, text: str | None = None, **attrs: str) -> Any:
    element = etree.SubElement(parent, f"{{{namespace}}}{tag}")
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
    return _cbc(parent, tag, format_money(value), currencyID=CURRENCY)


def _tax_scheme(parent: Any, code: str, name: str) -> None:
    category = _cac(parent, "TaxCategory")
    _cbc(category, "ID", code)
    _cbc(category, "Name", name)
    scheme = _cac(category, "TaxScheme")
    _cbc(scheme, "ID", code)
    _cbc(scheme, "Name", name)


def _build_party(
    parent: Any,
    *,
    identification: str,
    scheme_name: str,
    legal_name: str,
    address: str,
    municipality_code: str,
    department_code: str,
) -> None:
    party = _cac(parent, "Party")
    identification_element = _cac(party, "PartyIdentification")
    _cbc(identification_element, "ID", identification, schemeName=scheme_name)
    name = _cac(party, "PartyName")
    _cbc(name, "Name", legal_name)

    physical_location = _cac(party, "PhysicalLocation")
    address_element = _cac(physical_location, "Address")
    _cbc(address_element, "ID", municipality_code)
    _cbc(address_element, "CityName", municipality_code)
    _cbc(address_element, "CountrySubentity", department_code)
    _cbc(address_element, "CountrySubentityCode", department_code)
    line = _cac(address_element, "AddressLine")
    _cbc(line, "Line", address)
    country = _cac(address_element, "Country")
    _cbc(country, "IdentificationCode", COUNTRY_CODE)
    _cbc(country, "Name", COUNTRY_NAME)

    party_tax_scheme = _cac(party, "PartyTaxScheme")
    _cbc(party_tax_scheme, "RegistrationName", legal_name)
    _cbc(party_tax_scheme, "CompanyID", identification, schemeName=scheme_name)
    scheme = _cac(party_tax_scheme, "TaxScheme")
    _cbc(scheme, "ID", "01")
    _cbc(scheme, "Name", "IVA")

    legal_entity = _cac(party, "PartyLegalEntity")
    _cbc(legal_entity, "RegistrationName", legal_name)
    _cbc(legal_entity, "CompanyID", identification, schemeName=scheme_name)


def _build_dian_extensions(
    parent: Any,
    *,
    company: CompanySetting,
    document_number: str,
    security_code: str,
) -> None:
    extensions = _sub(parent, EXT_NS, "UBLExtensions")
    extension = _sub(extensions, EXT_NS, "UBLExtension")
    content = _sub(extension, EXT_NS, "ExtensionContent")
    dian = _sub(content, STS_NS, "DianExtensions")

    control = _sub(dian, STS_NS, "InvoiceControl")
    _sub(
        control,
        STS_NS,
        "InvoiceAuthorization",
        company.dian_resolution_number or "",
    )
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
    _sub(authorized, STS_NS, "Prefix", company.dian_resolution_prefix or "")
    _sub(authorized, STS_NS, "From", str(company.dian_resolution_range_from or 0))
    _sub(authorized, STS_NS, "To", str(company.dian_resolution_range_to or 0))

    source = _sub(dian, STS_NS, "InvoiceSource")
    _cbc(source, "IdentificationCode", COUNTRY_CODE)

    provider = _sub(dian, STS_NS, "SoftwareProvider")
    _sub(provider, STS_NS, "ProviderID", company.tax_id or "", schemeName="NIT")
    _sub(
        provider,
        STS_NS,
        "SoftwareID",
        company.dian_software_id or SOFTWARE_ID_FALLBACK,
    )
    _sub(dian, STS_NS, "SoftwareSecurityCode", security_code)

    authorization_provider = _sub(dian, STS_NS, "AuthorizationProvider")
    _sub(
        authorization_provider,
        STS_NS,
        "AuthorizationProviderID",
        DIAN_AUTHORITY_NIT,
        schemeName="NIT",
    )


def payroll_document_number(period: PayrollPeriod) -> str:
    """Identificador del documento: NE-<año>-<mes>."""
    return f"NE-{period.year}-{period.month:02d}"


def build_payroll_xml(
    *,
    period: PayrollPeriod,
    company: CompanySetting,
    rows: list[tuple[PayrollDetail, PayrollContribution]],
    employees: dict[uuid.UUID, Employee],
    cune: str,
    security_code: str,
    generation_date: date,
    issue_time: time,
) -> bytes:
    """Serializa la nómina del periodo como XML UBL 2.1 DIAN (UTF-8)."""
    document_number = payroll_document_number(period)
    total_devengado = sum((row[0].base_salary for row in rows), ZERO)
    total_deducciones = sum(
        (row[0].health_deduction + row[0].pension_deduction for row in rows),
        ZERO,
    )
    total_neto = sum((row[0].net_pay for row in rows), ZERO)

    root = etree.Element(f"{{{UBL_INVOICE_NS}}}Invoice", nsmap=NAMESPACES)

    _build_dian_extensions(
        root,
        company=company,
        document_number=document_number,
        security_code=security_code,
    )

    _cbc(root, "UBLVersionID", UBL_VERSION_ID)
    _cbc(root, "CustomizationID", CUSTOMIZATION_ID)
    _cbc(root, "ProfileID", PROFILE_ID)
    _cbc(root, "ID", document_number)
    _cbc(root, "UUID", cune, schemeName="CUNE-SHA384")
    _cbc(root, "IssueDate", generation_date.isoformat())
    _cbc(root, "IssueTime", f"{issue_time.strftime('%H:%M:%S')}-05:00")
    if period.payment_date is not None:
        _cbc(root, "DueDate", period.payment_date.isoformat())
    _cbc(root, "InvoiceTypeCode", INVOICE_TYPE_CODE)
    if period.notes_dian:
        _cbc(root, "Note", period.notes_dian)
    _cbc(root, "DocumentCurrencyCode", CURRENCY)
    _cbc(root, "LineCountNumeric", str(len(rows) * len(EARNED_CONCEPTS)))

    supplier = _cac(root, "AccountingSupplierParty")
    _build_party(
        supplier,
        identification=f"{company.tax_id}-{company.dv}",
        scheme_name="NIT",
        legal_name=company.name,
        address=company.address or "",
        municipality_code=company.dian_municipality_code or "",
        department_code=company.dian_department_code or "",
    )

    customer = _cac(root, "AccountingCustomerParty")
    first_detail = rows[0][0] if rows else None
    if first_detail is not None:
        employee = employees[first_detail.employee_id]
        _build_party(
            customer,
            identification=employee.document,
            scheme_name=employee.document_type or "CC",
            legal_name=f"{employee.first_name} {employee.last_name}",
            address=employee.address or "",
            municipality_code=employee.municipality_code or "",
            department_code=employee.department_code or "",
        )

    # Deducciones del empleado consolidadas por concepto.
    total_health = sum((row[0].health_deduction for row in rows), ZERO)
    total_pension = sum((row[0].pension_deduction for row in rows), ZERO)
    for code, label, amount in (
        ("SALUD", DEDUCTION_CONCEPTS[0][1], total_health),
        ("PENSION", DEDUCTION_CONCEPTS[1][1], total_pension),
    ):
        if amount <= ZERO:
            continue
        allowance = _cac(root, "AllowanceCharge")
        _cbc(allowance, "ChargeIndicator", "false")
        _cbc(allowance, "AllowanceChargeReason", f"{code} · {label}")
        _amount(allowance, "Amount", amount)

    # Aportes a cargo del empleador, un TaxTotal por concepto.
    for code, label, field in EMPLOYER_CONTRIBUTION_CONCEPTS:
        amount = sum((getattr(row[1], field) for row in rows), ZERO)
        if amount <= ZERO:
            continue
        tax_total = _cac(root, "TaxTotal")
        _amount(tax_total, "TaxAmount", amount)
        subtotal = _cac(tax_total, "TaxSubtotal")
        _amount(subtotal, "TaxableAmount", total_devengado)
        _amount(subtotal, "TaxAmount", amount)
        _tax_scheme(subtotal, code, label)

    monetary = _cac(root, "LegalMonetaryTotal")
    _amount(monetary, "LineExtensionAmount", total_devengado)
    _amount(monetary, "TaxExclusiveAmount", total_devengado)
    _amount(monetary, "TaxInclusiveAmount", total_devengado)
    _amount(monetary, "AllowanceTotalAmount", total_deducciones)
    _amount(monetary, "PayableAmount", total_neto)

    # Devengados: una InvoiceLine por concepto de cada empleado.
    line_index = 0
    for detail, contribution in rows:
        employee = employees[detail.employee_id]
        values = {
            "SALARIO": detail.base_salary,
            "CESANTIAS": contribution.severance,
            "INTCESANTIAS": contribution.severance_interest,
            "VACACIONES": contribution.vacation,
            "PRIMA": contribution.bonus,
        }
        for code, label in EARNED_CONCEPTS:
            amount = values.get(code, ZERO)
            if amount <= ZERO:
                continue
            line_index += 1
            line = _cac(root, "InvoiceLine")
            _cbc(line, "ID", str(line_index))
            _amount(line, "LineExtensionAmount", amount)
            item = _cac(line, "Item")
            _cbc(
                item,
                "Description",
                f"{code} · {label} · {employee.document} · "
                f"{employee.first_name} {employee.last_name}",
            )
            price = _cac(line, "Price")
            _amount(price, "PriceAmount", amount)

    return etree.tostring(
        root,
        xml_declaration=True,
        encoding="UTF-8",
        pretty_print=True,
    )


__all__ = [
    "DEDUCTION_CONCEPTS",
    "EARNED_CONCEPTS",
    "EMPLOYER_CONTRIBUTION_CONCEPTS",
    "build_payroll_xml",
    "payroll_document_number",
]
