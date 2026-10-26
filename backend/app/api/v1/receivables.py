"""Rutas de cartera: aging, estado de cuenta, recordatorios y acuerdos."""

from __future__ import annotations

from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies.auth import CurrentUser, get_current_user, require_role
from app.application.agreement_service import AgreementService
from app.application.receivables_schemas import (
    AgingReport,
    AgreementCreate,
    AgreementRead,
    AutoRemindRequest,
    AutoRemindResult,
    CustomerAging,
    CustomerStatement,
    InstallmentPayRequest,
    ReceivablesSummary,
    ReminderCreate,
    ReminderRead,
)
from app.application.receivables_service import ReceivablesService
from app.application.reminder_service import ReminderService
from app.domain.models.auth import UserRole
from app.domain.models.receivables import AgreementStatus
from app.infrastructure.database import get_db
from app.infrastructure.transactions import operation_transaction

router = APIRouter(
    prefix="/receivables",
    tags=["receivables"],
    dependencies=[Depends(get_current_user)],
)

DbSession = Annotated[Session, Depends(get_db)]

# Caja puede consultar cartera (lectura), pero no gestionar cobranza.
READ_ROLES = [UserRole.ADMIN, UserRole.ACCOUNTANT, UserRole.CASHIER]
WRITE_ROLES = [UserRole.ADMIN, UserRole.ACCOUNTANT]


def get_receivables_service(db: DbSession) -> ReceivablesService:
    """Construye el servicio de aging y estado de cuenta."""
    return ReceivablesService(db)


ReceivablesServiceDep = Annotated[
    ReceivablesService,
    Depends(get_receivables_service),
]


def get_reminder_service(db: DbSession) -> ReminderService:
    """Construye el servicio de recordatorios de cobranza."""
    return ReminderService(db)


ReminderServiceDep = Annotated[ReminderService, Depends(get_reminder_service)]


def get_agreement_service(db: DbSession) -> AgreementService:
    """Construye el servicio de acuerdos de pago."""
    return AgreementService(db)


AgreementServiceDep = Annotated[AgreementService, Depends(get_agreement_service)]


# -- Aging y estado de cuenta ----------------------------------------------


@router.get(
    "/aging",
    response_model=AgingReport,
    dependencies=[Depends(require_role(READ_ROLES))],
)
def get_aging(
    service: ReceivablesServiceDep,
    as_of_date: Annotated[date | None, Query()] = None,
) -> AgingReport:
    """Aging por cliente a la fecha de corte (hoy por defecto)."""
    return service.compute_aging(as_of_date=as_of_date)


@router.get(
    "/aging/{contact_id}",
    response_model=CustomerAging,
    dependencies=[Depends(require_role(READ_ROLES))],
)
def get_customer_aging(
    contact_id: UUID,
    service: ReceivablesServiceDep,
    as_of_date: Annotated[date | None, Query()] = None,
) -> CustomerAging:
    """Aging de un cliente concreto."""
    return service.compute_customer_aging(contact_id=contact_id, as_of_date=as_of_date)


@router.get(
    "/customers/{contact_id}/statement",
    response_model=CustomerStatement,
    dependencies=[Depends(require_role(READ_ROLES))],
)
def get_customer_statement(
    contact_id: UUID,
    service: ReceivablesServiceDep,
    from_date: Annotated[date | None, Query()] = None,
    to_date: Annotated[date | None, Query()] = None,
) -> CustomerStatement:
    """Estado de cuenta del cliente con saldo inicial y corrido."""
    today = date.today()
    start = from_date or date(today.year, 1, 1)
    end = to_date or today
    return service.get_statement(contact_id=contact_id, from_date=start, to_date=end)


@router.get(
    "/summary",
    response_model=ReceivablesSummary,
    dependencies=[Depends(require_role(READ_ROLES))],
)
def get_receivables_summary(
    service: ReceivablesServiceDep,
    as_of_date: Annotated[date | None, Query()] = None,
) -> ReceivablesSummary:
    """Totales globales de cartera y top 10 clientes por deuda."""
    return service.summary(as_of_date=as_of_date)


# -- Recordatorios ---------------------------------------------------------


@router.post(
    "/reminders",
    response_model=ReminderRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_role(WRITE_ROLES))],
)
def create_reminder(
    payload: ReminderCreate,
    current_user: CurrentUser,
    db: DbSession,
    service: ReminderServiceDep,
) -> ReminderRead:
    """Registra un recordatorio manual (anti-spam: mismo nivel en 24 h)."""
    with operation_transaction(db):
        reminder = service.send_reminder(
            invoice_id=payload.invoice_id,
            level=payload.level,
            channel=payload.channel,
            notes=payload.notes,
            created_by=current_user.id,
        )
    if reminder is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe un recordatorio de ese nivel en las últimas 24 horas",
        )
    return ReminderRead.model_validate(reminder)


@router.get(
    "/reminders",
    response_model=list[ReminderRead],
    dependencies=[Depends(require_role(WRITE_ROLES))],
)
def list_reminders(
    service: ReminderServiceDep,
    invoice_id: Annotated[UUID | None, Query()] = None,
    contact_id: Annotated[UUID | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[ReminderRead]:
    """Historial de recordatorios filtrable por factura o cliente."""
    reminders = service.list_reminders(
        invoice_id=invoice_id,
        contact_id=contact_id,
        limit=limit,
        offset=offset,
    )
    return [ReminderRead.model_validate(item) for item in reminders]


@router.post(
    "/reminders/auto",
    response_model=AutoRemindResult,
    dependencies=[Depends(require_role(WRITE_ROLES))],
)
def run_auto_reminders(
    payload: AutoRemindRequest,
    current_user: CurrentUser,
    db: DbSession,
    service: ReminderServiceDep,
) -> AutoRemindResult:
    """Ejecuta el job manual de recordatorios para facturas vencidas."""
    with operation_transaction(db):
        result = service.auto_remind_overdue(
            as_of_date=payload.as_of_date,
            created_by=current_user.id,
        )
    return AutoRemindResult(**result)


# -- Acuerdos de pago ------------------------------------------------------


@router.post(
    "/agreements",
    response_model=AgreementRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_role(WRITE_ROLES))],
)
def create_agreement(
    payload: AgreementCreate,
    current_user: CurrentUser,
    db: DbSession,
    service: AgreementServiceDep,
) -> AgreementRead:
    """Crea un acuerdo de pago y genera sus cuotas automáticamente."""
    with operation_transaction(db):
        agreement = service.create(
            contact_id=payload.contact_id,
            invoice_id=payload.invoice_id,
            total_amount=payload.total_amount,
            installments=payload.installments,
            start_date=payload.start_date,
            frequency_days=payload.frequency_days,
            notes=payload.notes,
            created_by=current_user.id,
        )
    return AgreementRead.model_validate(agreement)


@router.get(
    "/agreements",
    response_model=list[AgreementRead],
    dependencies=[Depends(require_role(WRITE_ROLES))],
)
def list_agreements(
    service: AgreementServiceDep,
    contact_id: Annotated[UUID | None, Query()] = None,
    status_filter: Annotated[AgreementStatus | None, Query(alias="status")] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[AgreementRead]:
    """Lista acuerdos con filtros por cliente y estado."""
    agreements = service.list(
        contact_id=contact_id,
        status=status_filter,
        limit=limit,
        offset=offset,
    )
    return [AgreementRead.model_validate(item) for item in agreements]


@router.get(
    "/agreements/{agreement_id}",
    response_model=AgreementRead,
    dependencies=[Depends(require_role(WRITE_ROLES))],
)
def get_agreement(
    agreement_id: UUID,
    service: AgreementServiceDep,
) -> AgreementRead:
    """Detalle del acuerdo con todas sus cuotas."""
    return AgreementRead.model_validate(service.get(agreement_id))


@router.post(
    "/agreements/{agreement_id}/installments/{installment_id}/pay",
    response_model=AgreementRead,
    dependencies=[Depends(require_role(WRITE_ROLES))],
)
def pay_installment(
    agreement_id: UUID,
    installment_id: UUID,
    payload: InstallmentPayRequest,
    current_user: CurrentUser,
    db: DbSession,
    service: AgreementServiceDep,
) -> AgreementRead:
    """Registra un abono a una cuota; no genera contabilidad."""
    with operation_transaction(db):
        agreement = service.register_installment_payment(
            agreement_id=agreement_id,
            installment_id=installment_id,
            amount=payload.amount,
            paid_by=current_user.id,
        )
    return AgreementRead.model_validate(agreement)


@router.post(
    "/agreements/{agreement_id}/cancel",
    response_model=AgreementRead,
    dependencies=[Depends(require_role(WRITE_ROLES))],
)
def cancel_agreement(
    agreement_id: UUID,
    db: DbSession,
    service: AgreementServiceDep,
) -> AgreementRead:
    """Cancela un acuerdo; los abonos ya registrados se conservan."""
    with operation_transaction(db):
        agreement = service.cancel(agreement_id)
    return AgreementRead.model_validate(agreement)


@router.post(
    "/agreements/{agreement_id}/mark-broken",
    response_model=AgreementRead,
    dependencies=[Depends(require_role([UserRole.ADMIN]))],
)
def mark_agreement_broken(
    agreement_id: UUID,
    db: DbSession,
    service: AgreementServiceDep,
) -> AgreementRead:
    """Marca un acuerdo activo como incumplido (solo ADMIN)."""
    with operation_transaction(db):
        agreement = service.mark_broken(agreement_id)
    return AgreementRead.model_validate(agreement)


__all__ = ["router"]
