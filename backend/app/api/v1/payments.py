"""Rutas de pagos sobre facturas emitidas."""

from __future__ import annotations

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Response, status
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.application.accounting.service import AccountingService
from app.application.payment_schemas import (
    PaymentCreate,
    PaymentRead,
    canonical_payment_hash,
)
from app.domain.calculations import round_money
from app.domain.exceptions import InvoiceStateError, ResourceNotFoundError
from app.domain.models.idempotency_key import IdempotencyKey
from app.domain.models.invoice import LifecycleStatus
from app.domain.payment_repository import PaymentRepository
from app.infrastructure.database import get_db
from app.infrastructure.transactions import operation_transaction

router = APIRouter(prefix="/invoices", tags=["payments"])

DbSession = Annotated[Session, Depends(get_db)]
IdempotencyKeyHeader = Annotated[UUID, Header(alias="Idempotency-Key")]

IDEMPOTENCY_MISMATCH = "Idempotency-Key reutilizada con body diferente"
PAYMENT_ONLY_ISSUED = "Solo se puede pagar una factura emitida"
OVERPAYMENT_NOT_ALLOWED = "Sobrepago no permitido en MVP"
DELETE_ONLY_ISSUED = "Solo se pueden eliminar pagos de facturas emitidas"


def get_payment_repository(db: DbSession) -> PaymentRepository:
    """Construye el repositorio con la sesión de la petición."""
    return PaymentRepository(db)


PaymentRepositoryDep = Annotated[PaymentRepository, Depends(get_payment_repository)]


def _replay_response(
    existing: IdempotencyKey | None,
    request_hash: str,
) -> dict[str, Any] | None:
    """Valida una Key existente y devuelve la respuesta guardada, si aplica."""
    if existing is None:
        return None
    if existing.request_hash != request_hash:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=IDEMPOTENCY_MISMATCH,
        )
    if existing.response_body is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Idempotency-Key en proceso",
        )
    return existing.response_body


@router.post(
    "/{invoice_id}/payments",
    response_model=PaymentRead,
    status_code=status.HTTP_201_CREATED,
)
def create_payment(
    invoice_id: UUID,
    payload: PaymentCreate,
    idempotency_key: IdempotencyKeyHeader,
    db: DbSession,
    repository: PaymentRepositoryDep,
) -> JSONResponse:
    """Registra un pago, actualiza la factura y aplica idempotencia por body."""
    key = str(idempotency_key)
    request_hash = canonical_payment_hash(payload)
    response_body: dict[str, Any] | None = None

    try:
        with operation_transaction(db):
            response_body = _replay_response(
                repository.get_idempotency_key(key),
                request_hash,
            )
            if response_body is None:
                invoice = repository.get_invoice_for_update(invoice_id)
                if invoice is None:
                    raise ResourceNotFoundError("Factura no encontrada")

                # Revisar de nuevo tras adquirir el lock: otra petición con la
                # misma Key pudo terminar mientras esperábamos la factura.
                response_body = _replay_response(
                    repository.get_idempotency_key(key),
                    request_hash,
                )
                if response_body is None:
                    if invoice.lifecycle_status is not LifecycleStatus.ISSUED:
                        raise InvoiceStateError(PAYMENT_ONLY_ISSUED)

                    amount = round_money(payload.amount)
                    if amount > repository.current_balance(invoice):
                        raise HTTPException(
                            status_code=422,
                            detail=OVERPAYMENT_NOT_ALLOWED,
                        )

                    payment = repository.create_payment(
                        invoice_id=invoice.id,
                        amount=amount,
                        payment_date=payload.payment_date,
                        method=payload.method,
                        reference=payload.reference,
                    )
                    repository.recalculate_invoice(invoice)
                    AccountingService(db).record_payment(payment, invoice)
                    response_body = PaymentRead.model_validate(payment).model_dump(mode="json")
                    repository.add_idempotency_key(
                        key=key,
                        request_hash=request_hash,
                        response_body=response_body,
                    )
    except IntegrityError:
        # Otra petición concurrente insertó la misma Key. Su transacción ganó y
        # esta se revirtió por completo, incluido el pago y el ajuste de saldo.
        winner_body = _replay_response(
            repository.get_idempotency_key(key),
            request_hash,
        )
        if winner_body is None:
            raise
        response_body = winner_body

    if response_body is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Idempotency-Key en proceso",
        )
    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content=response_body,
    )


@router.get("/{invoice_id}/payments", response_model=list[PaymentRead])
def list_payments(
    invoice_id: UUID,
    repository: PaymentRepositoryDep,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[PaymentRead]:
    """Lista los pagos de una factura por fecha descendente."""
    invoice = repository.get_invoice(invoice_id)
    if invoice is None:
        raise ResourceNotFoundError("Factura no encontrada")
    payments = repository.list_payments(invoice_id, limit=limit, offset=offset)
    return [PaymentRead.model_validate(payment) for payment in payments]


@router.delete(
    "/{invoice_id}/payments/{payment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_payment(
    invoice_id: UUID,
    payment_id: UUID,
    db: DbSession,
    repository: PaymentRepositoryDep,
) -> Response:
    """Elimina un pago y recalcula la factura en la misma transacción."""
    with operation_transaction(db):
        invoice = repository.get_invoice_for_update(invoice_id)
        if invoice is None:
            raise ResourceNotFoundError("Factura no encontrada")
        if invoice.lifecycle_status is not LifecycleStatus.ISSUED:
            raise InvoiceStateError(DELETE_ONLY_ISSUED)

        payment = repository.get_payment_for_update(invoice_id, payment_id)
        if payment is None:
            raise ResourceNotFoundError("Pago no encontrado")

        AccountingService(db).record_payment_reversal(payment, invoice)
        repository.delete_payment(payment)
        repository.recalculate_invoice(invoice)

    return Response(status_code=status.HTTP_204_NO_CONTENT)
