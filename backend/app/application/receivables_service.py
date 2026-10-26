"""Servicio de cartera: aging y estado de cuenta.

Todo el cálculo es derivado y se hace en lectura; no existe ninguna tabla de
saldos ni de buckets. Los importes usan ``Decimal`` y se cuantizan a dos
decimales con ``round_money``.

El aging parte de la fuente real de movimientos:
``saldo = factura.total - SUM(pagos) - SUM(notas crédito emitidas)``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal
from uuid import UUID

from sqlalchemy.orm import Session

from app.application.receivables_schemas import (
    AgingBuckets,
    AgingReport,
    CustomerAging,
    CustomerStatement,
    ReceivablesSummary,
    StatementLine,
)
from app.domain.calculations import round_money
from app.domain.exceptions import ReceivablesValidationError, ResourceNotFoundError
from app.domain.receivables_repository import ReceivablesRepository

ZERO = Decimal("0.00")
DEFAULT_PAYMENT_TERMS_DAYS = 30
AGING_BUCKET_FIELDS = (
    "current",
    "d0_30",
    "d31_60",
    "d61_90",
    "d91_120",
    "d120_plus",
)
TOP_CUSTOMERS = 10


@dataclass
class _CustomerAccumulator:
    contact_name: str
    invoice_count: int = 0
    buckets: dict[str, Decimal] = field(
        default_factory=lambda: {name: ZERO for name in AGING_BUCKET_FIELDS}
    )

    @property
    def total(self) -> Decimal:
        return sum(self.buckets.values(), ZERO)


def bucket_for_days_overdue(days_overdue: int) -> str:
    """Clasifica los días vencidos en el bucket de aging correspondiente.

    Una factura que vence hoy o a futuro (``days_overdue <= 0``) es cartera
    corriente. Los rangos son inclusivos: 1-30, 31-60, 61-90, 91-120 y 120+.
    """
    if days_overdue <= 0:
        return "current"
    if days_overdue <= 30:
        return "d0_30"
    if days_overdue <= 60:
        return "d31_60"
    if days_overdue <= 90:
        return "d61_90"
    if days_overdue <= 120:
        return "d91_120"
    return "d120_plus"


class ReceivablesService:
    """Aging por cliente, estado de cuenta y resumen global de cartera."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.repository = ReceivablesRepository(db)

    def compute_aging(self, *, as_of_date: date | None = None) -> AgingReport:
        """Construye el aging completo agrupado por cliente."""
        as_of = as_of_date or date.today()
        rows = self.repository.list_outstanding_invoices(as_of_date=as_of)

        grouped: dict[UUID, _CustomerAccumulator] = {}
        for row in rows:
            if row.due_date is not None:
                due_date = row.due_date
            elif row.issue_date is not None:
                due_date = row.issue_date + timedelta(days=DEFAULT_PAYMENT_TERMS_DAYS)
            else:
                due_date = as_of
            days_overdue = (as_of - due_date).days
            bucket = bucket_for_days_overdue(days_overdue)

            accumulator = grouped.get(row.contact_id)
            if accumulator is None:
                accumulator = _CustomerAccumulator(contact_name=row.contact_name)
                grouped[row.contact_id] = accumulator
            accumulator.invoice_count += 1
            accumulator.buckets[bucket] += row.outstanding

        by_customer = self._build_customer_rows(grouped)
        buckets_totals = self._totals(by_customer)
        return AgingReport(
            as_of_date=as_of,
            buckets_totals=buckets_totals,
            by_customer=by_customer,
            total_overdue=round_money(buckets_totals.total - buckets_totals.current),
        )

    def compute_customer_aging(
        self,
        *,
        contact_id: UUID,
        as_of_date: date | None = None,
    ) -> CustomerAging:
        """Aging de un único cliente; ceros si no tiene cartera pendiente."""
        contact = self.repository.get_contact(contact_id)
        if contact is None:
            raise ResourceNotFoundError("Contacto no encontrado")

        report = self.compute_aging(as_of_date=as_of_date)
        for row in report.by_customer:
            if row.contact_id == contact_id:
                return row
        return CustomerAging(
            contact_id=contact_id,
            contact_name=contact.name,
            current=ZERO,
            d0_30=ZERO,
            d31_60=ZERO,
            d61_90=ZERO,
            d91_120=ZERO,
            d120_plus=ZERO,
            total=ZERO,
            total_overdue=ZERO,
            invoice_count=0,
        )

    def summary(self, *, as_of_date: date | None = None) -> ReceivablesSummary:
        """Totales globales y top 10 clientes por deuda."""
        report = self.compute_aging(as_of_date=as_of_date)
        return ReceivablesSummary(
            as_of_date=report.as_of_date,
            buckets_totals=report.buckets_totals,
            total_overdue=report.total_overdue,
            top_customers=report.by_customer[:TOP_CUSTOMERS],
            customer_count=len(report.by_customer),
        )

    def get_statement(
        self,
        *,
        contact_id: UUID,
        from_date: date,
        to_date: date,
    ) -> CustomerStatement:
        """Estado de cuenta cronológico con saldo inicial y corrido."""
        if from_date > to_date:
            raise ReceivablesValidationError("La fecha inicial no puede ser mayor que la final")

        contact = self.repository.get_contact(contact_id)
        if contact is None:
            raise ResourceNotFoundError("Contacto no encontrado")

        movements: list[tuple[date, int, StatementLine]] = []

        for invoice in self.repository.statement_invoices(
            contact_id=contact_id,
            to_date=to_date,
        ):
            movement_date = invoice.issue_date or invoice.created_at.date()
            reference = invoice.number or f"FAC-{str(invoice.invoice_id)[:8].upper()}"
            movements.append(
                (
                    movement_date,
                    0,
                    StatementLine(
                        date=movement_date,
                        type="INVOICE",
                        reference=reference,
                        description=f"Factura de venta {reference}",
                        debit=invoice.total,
                        credit=ZERO,
                        running_balance=ZERO,
                    ),
                )
            )

        for payment in self.repository.statement_payments(
            contact_id=contact_id,
            to_date=to_date,
        ):
            reference = (
                payment.reference
                or payment.invoice_number
                or f"PAG-{str(payment.payment_id)[:8].upper()}"
            )
            movements.append(
                (
                    payment.payment_date,
                    1,
                    StatementLine(
                        date=payment.payment_date,
                        type="PAYMENT",
                        reference=reference,
                        description=(
                            f"Pago {payment.method} factura {payment.invoice_number or '-'}"
                        ),
                        debit=ZERO,
                        credit=payment.amount,
                        running_balance=ZERO,
                    ),
                )
            )

        for note in self.repository.statement_credit_notes(
            contact_id=contact_id,
            to_date=to_date,
        ):
            movement_date = note.issue_date or note.created_at.date()
            reference = note.number or f"NC-{str(note.credit_note_id)[:8].upper()}"
            movements.append(
                (
                    movement_date,
                    2,
                    StatementLine(
                        date=movement_date,
                        type="CREDIT_NOTE",
                        reference=reference,
                        description=f"Nota crédito {reference} sobre factura "
                        f"{note.invoice_number or '-'}",
                        debit=ZERO,
                        credit=note.total,
                        running_balance=ZERO,
                    ),
                )
            )

        movements.sort(key=lambda item: (item[0], item[1]))

        opening = ZERO
        for movement_date, _order, line in movements:
            if movement_date < from_date:
                opening += line.debit - line.credit
        opening = round_money(opening)

        running = opening
        lines: list[StatementLine] = []
        for movement_date, _order, line in movements:
            if movement_date < from_date:
                continue
            running = round_money(running + line.debit - line.credit)
            lines.append(line.model_copy(update={"running_balance": running}))

        return CustomerStatement(
            contact_id=contact_id,
            contact_name=contact.name,
            from_date=from_date,
            to_date=to_date,
            opening_balance=opening,
            lines=lines,
            closing_balance=round_money(running),
        )

    # -- Helpers ----------------------------------------------------------

    def _build_customer_rows(
        self,
        grouped: dict[UUID, _CustomerAccumulator],
    ) -> list[CustomerAging]:
        rows: list[CustomerAging] = []
        for contact_id, accumulator in grouped.items():
            total = round_money(accumulator.total)
            current = round_money(accumulator.buckets["current"])
            rows.append(
                CustomerAging(
                    contact_id=contact_id,
                    contact_name=accumulator.contact_name,
                    current=round_money(accumulator.buckets["current"]),
                    d0_30=round_money(accumulator.buckets["d0_30"]),
                    d31_60=round_money(accumulator.buckets["d31_60"]),
                    d61_90=round_money(accumulator.buckets["d61_90"]),
                    d91_120=round_money(accumulator.buckets["d91_120"]),
                    d120_plus=round_money(accumulator.buckets["d120_plus"]),
                    total=total,
                    total_overdue=round_money(total - current),
                    invoice_count=accumulator.invoice_count,
                )
            )
        rows.sort(key=lambda row: (-row.total, row.contact_name.lower()))
        return rows

    def _totals(self, rows: list[CustomerAging]) -> AgingBuckets:
        totals = {name: ZERO for name in AGING_BUCKET_FIELDS}
        for row in rows:
            for name in AGING_BUCKET_FIELDS:
                totals[name] += getattr(row, name)
        return AgingBuckets(
            current=round_money(totals["current"]),
            d0_30=round_money(totals["d0_30"]),
            d31_60=round_money(totals["d31_60"]),
            d61_90=round_money(totals["d61_90"]),
            d91_120=round_money(totals["d91_120"]),
            d120_plus=round_money(totals["d120_plus"]),
            total=round_money(sum(totals.values(), ZERO)),
        )


__all__ = [
    "AGING_BUCKET_FIELDS",
    "DEFAULT_PAYMENT_TERMS_DAYS",
    "ReceivablesService",
    "bucket_for_days_overdue",
]
