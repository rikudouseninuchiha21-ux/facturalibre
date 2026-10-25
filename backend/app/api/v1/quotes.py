"""Rutas de creación, listado, consulta, eliminación y conversión de cotizaciones."""

from decimal import Decimal
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Response, status
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.dependencies.auth import get_current_user, require_role
from app.application.quote_schemas import (
    QuoteCreate,
    QuoteRead,
    QuoteStatusUpdate,
    canonical_body_hash,
)
from app.application.quote_service import QuoteService
from app.domain.calculations import (
    LineAmounts,
    calculate_invoice_totals,
    calculate_line,
)
from app.domain.contact_repository import ContactRepository
from app.domain.exceptions import QuoteStateError, ResourceNotFoundError
from app.domain.item_repository import ItemRepository
from app.domain.models.auth import UserRole
from app.domain.models.quote import QuoteStatus
from app.domain.quote_repository import NewQuoteLine, QuoteRepository
from app.infrastructure.database import get_db
from app.infrastructure.transactions import operation_transaction

router = APIRouter(
    prefix="/quotes",
    tags=["quotes"],
    dependencies=[
        Depends(get_current_user),
        Depends(require_role([UserRole.ACCOUNTANT, UserRole.ADMIN])),
    ],
)

DbSession = Annotated[Session, Depends(get_db)]
IdempotencyKeyHeader = Annotated[UUID, Header(alias="Idempotency-Key")]

IDEMPOTENCY_MISMATCH = "Idempotency-Key reutilizada con body diferente"


def get_quote_repository(db: DbSession) -> QuoteRepository:
    """Construye el repositorio con la sesión de la petición."""
    return QuoteRepository(db)


QuoteRepositoryDep = Annotated[QuoteRepository, Depends(get_quote_repository)]


def get_quote_service(db: DbSession) -> QuoteService:
    """Construye el servicio de cotizaciones con la sesión de la petición."""
    return QuoteService(db)


QuoteServiceDep = Annotated[QuoteService, Depends(get_quote_service)]


@router.post("", response_model=QuoteRead, status_code=status.HTTP_201_CREATED)
def create_quote(
    payload: QuoteCreate,
    idempotency_key: IdempotencyKeyHeader,
    db: DbSession,
    repository: QuoteRepositoryDep,
    service: QuoteServiceDep,
) -> JSONResponse:
    """Crea una cotización DRAFT aplicando idempotencia por body."""
    key = str(idempotency_key)
    request_hash = canonical_body_hash(payload)

    existing = repository.get_idempotency_key(key)
    if existing is not None:
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
        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content=existing.response_body,
        )

    contact = ContactRepository(db).get_by_id(payload.contact_id)
    if contact is None:
        raise HTTPException(
            status_code=422,
            detail="contact_id no existe o está eliminado",
        )

    item_repository = ItemRepository(db)
    calculated_lines: list[LineAmounts] = []
    new_lines: list[NewQuoteLine] = []

    for line in payload.lines:
        item = item_repository.get_by_id(line.item_id)
        if item is None:
            raise HTTPException(
                status_code=422,
                detail=f"item_id {line.item_id} no existe o está eliminado",
            )

        if line.tax_rate is not None:
            tax_rate = line.tax_rate
        elif item.tax is not None and item.tax.deleted_at is None:
            tax_rate = item.tax.rate
        else:
            tax_rate = Decimal("0")

        description = line.description or item.description or item.name
        amounts = calculate_line(
            quantity=line.quantity,
            unit_price=line.unit_price,
            discount_percent=Decimal("0"),
            tax_rate=tax_rate,
            price_includes_tax=item.price_includes_tax,
        )
        calculated_lines.append(amounts)
        new_lines.append(
            NewQuoteLine(
                item_id=item.id,
                description=description,
                quantity=line.quantity,
                unit_price=line.unit_price,
                tax_rate=tax_rate,
                subtotal=amounts.subtotal,
                tax=amounts.tax,
                total=amounts.total,
            )
        )

    totals = calculate_invoice_totals(calculated_lines)
    quote = repository.create_draft(
        contact_id=contact.id,
        issue_date=payload.issue_date,
        expiry_date=payload.expiry_date,
        currency=payload.currency,
        lines=new_lines,
        subtotal=totals.subtotal,
        tax_total=totals.tax_total,
        total=totals.total,
    )

    quote.contact_name = contact.name  # type: ignore[attr-defined]
    response_body = QuoteRead.model_validate(quote).model_dump(mode="json")
    repository.add_idempotency_key(
        key=key,
        request_hash=request_hash,
        response_body=response_body,
    )

    try:
        repository.commit()
    except IntegrityError:
        repository.rollback()
        winner = repository.get_idempotency_key(key)
        if winner is None:
            raise
        if winner.request_hash != request_hash:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=IDEMPOTENCY_MISMATCH,
            ) from None
        if winner.response_body is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Idempotency-Key en proceso",
            ) from None
        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content=winner.response_body,
        )

    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content=response_body,
    )


@router.post("/{quote_id}/convert-to-invoice", response_model=QuoteRead)
def convert_quote_to_invoice(
    quote_id: UUID,
    db: DbSession,
    service: QuoteServiceDep,
    repository: QuoteRepositoryDep,
) -> QuoteRead:
    """Convierte una cotización ACEPTADA en una factura emitida.

    Solo funciona si la cotización está en estado ACCEPTED. Crea una factura
    real, descuenta stock, genera el asiento contable, cambia el contacto a
    CUSTOMER y marca la cotización como CONVERTED.
    """
    with operation_transaction(db):
        service.convert_to_invoice(quote_id)

    converted = repository.get_by_id(quote_id)
    if converted is None:
        raise ResourceNotFoundError("Cotización no encontrada")
    quote, contact_name = converted
    quote.contact_name = contact_name  # type: ignore[attr-defined]
    return QuoteRead.model_validate(quote)


@router.get("/{quote_id}", response_model=QuoteRead)
def get_quote(
    quote_id: UUID,
    repository: QuoteRepositoryDep,
) -> QuoteRead:
    """Obtiene una cotización con sus líneas y el nombre del contacto."""
    result = repository.get_by_id(quote_id)
    if result is None:
        raise ResourceNotFoundError("Cotización no encontrada")
    quote, contact_name = result
    quote.contact_name = contact_name  # type: ignore[attr-defined]
    return QuoteRead.model_validate(quote)


@router.patch("/{quote_id}/status", response_model=QuoteRead)
def update_quote_status(
    quote_id: UUID,
    payload: QuoteStatusUpdate,
    db: DbSession,
    repository: QuoteRepositoryDep,
) -> QuoteRead:
    """Cambia el estado de una cotización.

    Transiciones permitidas:
    - DRAFT -> SENT
    - SENT -> ACCEPTED
    - SENT -> REJECTED
    """
    quote = repository.get_by_id(quote_id)
    if quote is None:
        raise ResourceNotFoundError("Cotización no encontrada")
    quote_obj, contact_name = quote

    current = quote_obj.status
    new = payload.status

    allowed = {
        QuoteStatus.DRAFT: {QuoteStatus.SENT},
        QuoteStatus.SENT: {QuoteStatus.ACCEPTED, QuoteStatus.REJECTED},
    }
    if new not in allowed.get(current, set()):
        raise QuoteStateError(f"No se puede pasar de {current.value} a {new.value}")

    quote_obj.contact_name = contact_name  # type: ignore[attr-defined]
    with operation_transaction(db):
        updated = repository.update_status(
            quote_id,
            expected_status=current,
            new_status=new,
        )
    updated.contact_name = contact_name  # type: ignore[attr-defined]
    return QuoteRead.model_validate(updated)


@router.get("", response_model=list[QuoteRead])
def list_quotes(
    repository: QuoteRepositoryDep,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[QuoteRead]:
    """Lista cotizaciones con paginación por offset y nombre de contacto."""
    quotes = repository.list(limit=limit, offset=offset)
    result: list[QuoteRead] = []
    for quote, contact_name in quotes:
        quote.contact_name = contact_name  # type: ignore[attr-defined]
        result.append(QuoteRead.model_validate(quote))
    return result


@router.delete("/{quote_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_quote(
    quote_id: UUID,
    db: DbSession,
    repository: QuoteRepositoryDep,
) -> Response:
    """Elimina una cotización únicamente si está en DRAFT."""
    with operation_transaction(db):
        repository.soft_delete(quote_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
