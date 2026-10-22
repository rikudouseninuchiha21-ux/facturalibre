"""Mapeo inicial entre conceptos de facturación y cuentas del PUC colombiano.

REQUIERE VALIDACIÓN: contador público colombiano. Los códigos y nombres
seleccionados son una configuración inicial del MVP; la empresa debe confirmar
las cuentas auxiliares según su PUC, actividad económica y políticas contables.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AccountingMapping:
    """Cuentas usadas para generar los asientos automáticos."""

    accounts_receivable: str
    sales_revenue: str
    vat_payable: str
    cash: str
    bank: str
    payroll_expense: str = "510506"
    payroll_payable: str = "250505"
    payroll_contributions: str = "237005"


# Códigos provisionales, alineados con los grupos 1305, 4135, 2408, 1105, 1110
# y las cuentas de nómina 510506, 250505 y 237005.
DEFAULT_ACCOUNTING_MAPPING = AccountingMapping(
    accounts_receivable="130505",
    sales_revenue="413505",
    vat_payable="240801",
    cash="110505",
    bank="111005",
)

# El método de pago es texto libre en el MVP. Solo estos valores se consideran
# efectivo; cualquier otro se contabiliza como bancos.
CASH_PAYMENT_METHODS = frozenset({"cash", "efectivo", "caja"})
