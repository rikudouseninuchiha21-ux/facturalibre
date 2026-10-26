"""Recordatorios de cobranza con anti-spam y notificación in-app.

Reglas:
- Solo se recuerdan facturas ISSUED con saldo pendiente > 0.
- Un mismo nivel no se repite dentro de las últimas 24 horas.
- La severidad de la notificación escala con el nivel (1-2 INFO,
  3 WARNING, 4-5 CRITICAL).
- El job ``auto_remind_overdue`` es idempotente: la segunda corrida dentro
  de la ventana de 7 días no crea duplicados.

El servicio no hace commit; la API envuelve la operación completa en
``operation_transaction`` para que recordatorio y notificación sean atómicos.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from sqlalchemy.orm import Session

from app.application.notification_service import NotificationService
from app.domain.exceptions import ReceivablesValidationError, ReminderError, ResourceNotFoundError
from app.domain.models.auth import User, UserRole
from app.domain.models.invoice import LifecycleStatus
from app.domain.models.notification import NotificationSeverity
from app.domain.models.receivables import PaymentReminder, ReminderChannel
from app.domain.receivables_repository import ReceivablesRepository

ZERO = Decimal("0.00")
DUPLICATE_WINDOW = timedelta(hours=24)
AUTO_WINDOW = timedelta(days=7)

SEVERITY_BY_LEVEL: dict[int, NotificationSeverity] = {
    1: NotificationSeverity.INFO,
    2: NotificationSeverity.INFO,
    3: NotificationSeverity.WARNING,
    4: NotificationSeverity.CRITICAL,
    5: NotificationSeverity.CRITICAL,
}


def suggested_level(days_overdue: int) -> int | None:
    """Nivel sugerido según los días vencidos (``None`` si aún no aplica)."""
    if days_overdue < 7:
        return None
    if days_overdue <= 15:
        return 1
    if days_overdue <= 30:
        return 2
    if days_overdue <= 45:
        return 3
    if days_overdue <= 60:
        return 4
    return 5


class ReminderService:
    """Registro manual y automático de recordatorios de cobranza."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.repository = ReceivablesRepository(db)
        self.notifications = NotificationService(db)

    def send_reminder(
        self,
        *,
        invoice_id: UUID,
        level: int,
        channel: ReminderChannel = ReminderChannel.IN_APP,
        notes: str | None = None,
        created_by: UUID,
    ) -> PaymentReminder | None:
        """Crea un recordatorio o retorna ``None`` si está duplicado (24 h)."""
        if level < 1 or level > 5:
            raise ReceivablesValidationError("El nivel debe estar entre 1 y 5")

        invoice = self.repository.get_invoice(invoice_id)
        if invoice is None:
            raise ResourceNotFoundError("Factura no encontrada")
        if invoice.lifecycle_status is not LifecycleStatus.ISSUED:
            raise ReminderError("Solo se envían recordatorios de facturas emitidas")

        outstanding = self.repository.outstanding_for_invoice(invoice)
        if outstanding <= ZERO:
            raise ReceivablesValidationError(
                "La factura no tiene saldo pendiente; no requiere recordatorio"
            )

        now = datetime.now(UTC)
        if self.repository.has_reminder_since(
            invoice_id=invoice_id,
            level=level,
            since=now - DUPLICATE_WINDOW,
        ):
            return None

        contact = invoice.contact
        reminder = self.repository.create_reminder(
            {
                "invoice_id": invoice.id,
                "contact_id": invoice.contact_id,
                "level": level,
                "channel": channel,
                "sent_at": now,
                "notes": notes,
                "created_by": created_by,
            }
        )
        self._notify(
            invoice_number=invoice.number,
            contact_id=invoice.contact_id,
            contact_name=contact.name,
            outstanding=outstanding,
            level=level,
            notes=notes,
            created_by=created_by,
        )
        return reminder

    def auto_remind_overdue(
        self,
        *,
        as_of_date: date | None = None,
        created_by: UUID,
    ) -> dict[str, int]:
        """Genera recordatorios para facturas vencidas (idempotente)."""
        as_of = as_of_date or date.today()
        now = datetime.now(UTC)
        recent = self.repository.remindable_invoice_ids(since=now - AUTO_WINDOW)

        created = 0
        skipped = 0
        errors = 0
        for row in self.repository.list_outstanding_invoices(as_of_date=as_of):
            due_date = row.due_date
            if due_date is None:
                due_date = row.issue_date + timedelta(days=30) if row.issue_date else as_of
            level = suggested_level((as_of - due_date).days)
            if level is None:
                skipped += 1
                continue
            if (row.invoice_id, level) in recent:
                skipped += 1
                continue
            try:
                reminder = self.send_reminder(
                    invoice_id=row.invoice_id,
                    level=level,
                    created_by=created_by,
                )
            except Exception:
                errors += 1
                continue
            if reminder is None:
                skipped += 1
            else:
                created += 1
                recent.add((row.invoice_id, level))

        return {"created": created, "skipped": skipped, "errors": errors}

    def list_reminders(
        self,
        *,
        invoice_id: UUID | None = None,
        contact_id: UUID | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[PaymentReminder]:
        return self.repository.list_reminders(
            invoice_id=invoice_id,
            contact_id=contact_id,
            limit=limit,
            offset=offset,
        )

    def _notify(
        self,
        *,
        invoice_number: str | None,
        contact_id: UUID,
        contact_name: str,
        outstanding: Decimal,
        level: int,
        notes: str | None,
        created_by: UUID,
    ) -> None:
        """Notifica a ADMIN y ACCOUNTANT (y al ejecutor si tiene otro rol)."""
        severity = SEVERITY_BY_LEVEL[level]
        reference = invoice_number or "-"
        body = (
            f"Factura {reference} de {contact_name} con saldo pendiente "
            f"de {outstanding:.2f}. Nivel {level} de 5."
        )
        if notes:
            body = f"{body} {notes}"
        link = f"/receivables/customers/{contact_id}"

        target_roles = [UserRole.ADMIN, UserRole.ACCOUNTANT]
        self.notifications.create_for_roles(
            roles=target_roles,
            category="PAYMENT_REMINDER",
            severity=severity,
            title=f"Recordatorio de cobranza nivel {level}: {contact_name}",
            body=body,
            link=link,
        )

        creator = self.db.get(User, created_by)
        creator_role = getattr(creator, "role", None)
        if creator_role is not None and creator_role not in target_roles:
            self.notifications.create(
                user_id=created_by,
                category="PAYMENT_REMINDER",
                severity=severity,
                title=f"Recordatorio de cobranza nivel {level}: {contact_name}",
                body=body,
                link=link,
            )


__all__ = ["ReminderService", "SEVERITY_BY_LEVEL", "suggested_level"]
