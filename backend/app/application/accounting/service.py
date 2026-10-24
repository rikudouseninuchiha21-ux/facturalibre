"""Generación automática de asientos contables de partida doble.

El servicio no hace commit. La API lo invoca dentro de la misma transacción que
la emisión, el pago o la anulación, de modo que si la contabilidad falla la
operación de facturación también se revierte.
"""

from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy.orm import Session

from app.application.accounting.mapping import (
    CASH_PAYMENT_METHODS,
    DEFAULT_ACCOUNTING_MAPPING,
    AccountingMapping,
)
from app.domain.accounting_repository import AccountingRepository
from app.domain.calculations import round_money
from app.domain.models.accounting import (
    AccountingEntry,
    AccountingEntryLine,
    AccountingEntryStatus,
    AccountingSourceType,
)
from app.domain.models.invoice import Invoice
from app.domain.models.payment import Payment
from app.domain.models.payroll import PayrollPeriod
from app.domain.models.purchase import PurchaseInvoice

ZERO = Decimal("0.00")


class AccountingError(Exception):
    """Error de configuración o de integridad del asiento contable."""


class AccountingImbalanceError(AccountingError):
    """El asiento no cumple la regla débitos = créditos."""


@dataclass(frozen=True)
class JournalLine:
    """Movimiento calculado antes de persistirse."""

    account_code: str
    debit: Decimal = ZERO
    credit: Decimal = ZERO


class AccountingService:
    """Traduce eventos de facturación a asientos contables balanceados."""

    def __init__(
        self,
        db: Session,
        mapping: AccountingMapping = DEFAULT_ACCOUNTING_MAPPING,
    ) -> None:
        self.repository = AccountingRepository(db)
        self.mapping = mapping

    def record_invoice_issued(self, invoice: Invoice) -> AccountingEntry | None:
        """Genera el asiento de emisión de una factura de venta.

        Débito a Cuentas por Cobrar por el total; crédito a Ingresos por el
        subtotal y a IVA generado por el impuesto.

        Una factura con total cero no representa un hecho económico contable y
        no genera asiento. REQUIERE VALIDACIÓN: confirmar si el negocio debe
        prohibir este tipo de facturas o manejarlas con una cuenta de orden.
        """
        if invoice.total <= ZERO:
            return None

        lines = [
            JournalLine(
                account_code=self.mapping.accounts_receivable,
                debit=invoice.total,
            ),
            JournalLine(
                account_code=self.mapping.sales_revenue,
                credit=invoice.subtotal,
            ),
        ]
        if invoice.tax_total > ZERO:
            lines.append(
                JournalLine(
                    account_code=self.mapping.vat_payable,
                    credit=invoice.tax_total,
                )
            )

        return self._post_entry(
            entry_date=invoice.issue_date or date.today(),
            description=f"Emisión factura {invoice.number or invoice.id}",
            source_type=AccountingSourceType.INVOICE,
            source_id=invoice.id,
            lines=lines,
        )

    def record_payment(self, payment: Payment, invoice: Invoice) -> AccountingEntry:
        """Genera el asiento de un pago recibido.

        Débito a Caja/Bancos y crédito a Cuentas por Cobrar.
        """
        payment_account = (
            self.mapping.cash
            if payment.method.strip().lower() in CASH_PAYMENT_METHODS
            else self.mapping.bank
        )
        return self._post_entry(
            entry_date=payment.payment_date,
            description=(f"Pago factura {invoice.number or invoice.id} ({payment.method})"),
            source_type=AccountingSourceType.PAYMENT,
            source_id=payment.id,
            lines=[
                JournalLine(account_code=payment_account, debit=payment.amount),
                JournalLine(
                    account_code=self.mapping.accounts_receivable,
                    credit=payment.amount,
                ),
            ],
        )

    def record_purchase_issued(self, purchase: PurchaseInvoice) -> AccountingEntry:
        """Genera el asiento de emisión de una factura de compra.

        Débito a Inventario por el subtotal, débito a IVA Descontable por el
        impuesto y crédito a Cuentas por Pagar por el total.
        """
        lines = [
            JournalLine(
                account_code=self.mapping.inventory_account,
                debit=purchase.subtotal,
            ),
        ]
        if purchase.tax_total > ZERO:
            lines.append(
                JournalLine(
                    account_code=self.mapping.vat_deductible_account,
                    debit=purchase.tax_total,
                )
            )
        lines.append(
            JournalLine(
                account_code=self.mapping.accounts_payable_account,
                credit=purchase.total,
            )
        )

        return self._post_entry(
            entry_date=purchase.issue_date or date.today(),
            description=f"Emisión factura de compra {purchase.number or purchase.id}",
            source_type=AccountingSourceType.PURCHASE,
            source_id=purchase.id,
            lines=lines,
        )

    def record_invoice_void(self, invoice: Invoice) -> AccountingEntry | None:
        """Genera el contra-asiento de una factura anulada.

        Revierte exactamente las líneas del asiento de emisión. Si la factura
        es histórica y no tiene asiento de emisión, no crea un asiento aislado;
        se requiere un backfill contable previo.
        """
        original = self.repository.get_entry_by_source(
            AccountingSourceType.INVOICE,
            invoice.id,
        )
        if original is None:
            return None

        return self._reverse_entry(
            original=original,
            entry_date=(
                invoice.voided_at.date() if invoice.voided_at is not None else date.today()
            ),
            description=f"Reversión anulación factura {invoice.number or invoice.id}",
            source_type=AccountingSourceType.VOID,
            source_id=invoice.id,
        )

    def record_payment_reversal(
        self,
        payment: Payment,
        invoice: Invoice,
    ) -> AccountingEntry | None:
        """Revierte el asiento de un pago que se elimina.

        Mantiene el ledger consistente cuando se borra un pago. Al igual que en
        la anulación, si el pago es histórico y no tiene asiento, no inventa un
        movimiento contable.
        """
        original = self.repository.get_entry_by_source(
            AccountingSourceType.PAYMENT,
            payment.id,
        )
        if original is None:
            return None

        return self._reverse_entry(
            original=original,
            entry_date=date.today(),
            description=(f"Reversión eliminación pago factura {invoice.number or invoice.id}"),
            source_type=AccountingSourceType.PAYMENT_REVERSAL,
            source_id=payment.id,
        )

    def record_payroll(self, period: PayrollPeriod) -> AccountingEntry | None:
        """Genera el asiento de liquidación de un periodo de nómina.

        Débito al gasto de sueldos por el total devengado; crédito a salarios
        por pagar por el neto y crédito a aportes de salud y pensión por las
        deducciones. El asiento se apoya en el detalle ya calculado y usa el
        último día del periodo como fecha contable.

        REQUIERE VALIDACIÓN: la cuenta 237005 agrupa aportes de salud y pensión
        del empleado. La retención en la fuente y los parafiscales del empleador
        no forman parte de esta fase y requerirían cuentas y asientos propios.
        """
        details = period.details
        if not details:
            return None

        gross = round_money(sum((detail.base_salary for detail in details), ZERO))
        if gross <= ZERO:
            return None

        net = round_money(sum((detail.net_pay for detail in details), ZERO))
        contributions = round_money(
            sum(
                (detail.health_deduction + detail.pension_deduction for detail in details),
                ZERO,
            )
        )

        lines = [
            JournalLine(account_code=self.mapping.payroll_expense, debit=gross),
        ]
        if net > ZERO:
            lines.append(JournalLine(account_code=self.mapping.payroll_payable, credit=net))
        if contributions > ZERO:
            lines.append(
                JournalLine(
                    account_code=self.mapping.payroll_contributions,
                    credit=contributions,
                )
            )

        return self._post_entry(
            entry_date=date(
                period.year,
                period.month,
                calendar.monthrange(period.year, period.month)[1],
            ),
            description=f"Liquidación de nómina {period.month:02d}/{period.year}",
            source_type=AccountingSourceType.PAYROLL,
            source_id=period.id,
            lines=lines,
        )

    def _reverse_entry(
        self,
        *,
        original: AccountingEntry,
        entry_date: date,
        description: str,
        source_type: AccountingSourceType,
        source_id: UUID,
    ) -> AccountingEntry:
        """Crea el contra-asiento intercambiando débitos y créditos."""
        lines = [
            JournalLine(
                account_code=line.account_code,
                debit=line.credit,
                credit=line.debit,
            )
            for line in original.lines
        ]
        return self._post_entry(
            entry_date=entry_date,
            description=description,
            source_type=source_type,
            source_id=source_id,
            lines=lines,
        )

    def _post_entry(
        self,
        *,
        entry_date: date,
        description: str,
        source_type: AccountingSourceType,
        source_id: UUID,
        lines: list[JournalLine],
    ) -> AccountingEntry:
        """Valida y persiste un asiento balanceado sin confirmar la transacción."""
        normalized: list[JournalLine] = []
        for line in lines:
            debit = round_money(line.debit)
            credit = round_money(line.credit)
            if debit < ZERO or credit < ZERO:
                raise AccountingError("Los débitos y créditos no pueden ser negativos")
            if (debit > ZERO) == (credit > ZERO):
                raise AccountingError(
                    "Cada movimiento debe tener exactamente un débito o un crédito positivo"
                )
            normalized.append(
                JournalLine(
                    account_code=line.account_code,
                    debit=debit,
                    credit=credit,
                )
            )

        if len(normalized) < 2:
            raise AccountingError("Un asiento debe tener al menos dos movimientos")

        total_debit = round_money(sum((line.debit for line in normalized), ZERO))
        total_credit = round_money(sum((line.credit for line in normalized), ZERO))
        if total_debit != total_credit:
            raise AccountingImbalanceError(
                f"Asiento desbalanceado: débitos {total_debit}, créditos {total_credit}"
            )

        accounts = self.repository.get_accounts_by_codes(line.account_code for line in normalized)
        missing_codes = {line.account_code for line in normalized} - accounts.keys()
        if missing_codes:
            missing = ", ".join(sorted(missing_codes))
            raise AccountingError(f"Cuentas PUC no configuradas: {missing}")

        if self.repository.get_entry_by_source(source_type, source_id) is not None:
            raise AccountingError(f"Ya existe un asiento para {source_type.value} {source_id}")

        entry = AccountingEntry(
            entry_date=entry_date,
            description=description,
            source_type=source_type,
            source_id=source_id,
            status=AccountingEntryStatus.POSTED,
            lines=[
                AccountingEntryLine(
                    account_code=line.account_code,
                    debit=line.debit,
                    credit=line.credit,
                )
                for line in normalized
            ],
        )
        return self.repository.add_entry(entry)
