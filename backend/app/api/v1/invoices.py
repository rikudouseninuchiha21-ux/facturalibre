"""Rutas de creación, emisión y consulta de facturas."""

from decimal import Decimal
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Response, status
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.application.invoice_schemas import (
    InvoiceCreate,
    InvoiceRead,
    VoidInvoiceRequest,
    canonical_body_hash,
)
from app.domain.calculations import (
    LineAmounts,
    calculate_invoice_totals,
    calculate_line,
)
from app.domain.contact_repository import ContactRepository
from app.domain.exceptions import ResourceNotFoundError
from app.domain.invoice_repository import InvoiceRepository, NewInvoiceLine
from app.domain.item_repository import ItemRepository
from app.infrastructure.database import get_db

router = APIRouter(prefix="/invoices", tags=["invoices"])

DbSession = Annotated[Session, Depends(get_db)]
IdempotencyKeyHeader = Annotated[UUID, Header(alias="Idempotency-Key")]

IDEMPOTENCY_MISMATCH = "Idempotency-Key reutilizada con body diferente"


def get_invoice_repository(db: DbSession) -> InvoiceRepository:
    """Construye el repositorio con la sesión de la petición."""
    return InvoiceRepository(db)


InvoiceRepositoryDep = Annotated[InvoiceRepository, Depends(get_invoice_repository)]


@router.post("", response_model=InvoiceRead, status_code=status.HTTP_201_CREATED)
def create_invoice(
    payload: InvoiceCreate,
    idempotency_key: IdempotencyKeyHeader,
    db: DbSession,
    repository: InvoiceRepositoryDep,
) -> JSONResponse:
    """Crea una factura DRAFT aplicando idempotencia por body."""
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
    new_lines: list[NewInvoiceLine] = []

    for line in payload.lines:
        item = item_repository.get_by_id(line.item_id)
        if item is None:
            raise HTTPException(
                status_code=422,
                detail=f"item_id {line.item_id} no existe o está eliminado",
            )

        # REQUIERE VALIDACIÓN: contador/experto DIAN. La tarifa por defecto y el
        # código de impuesto deben alinearse con el catálogo tributario oficial.
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
            discount_percent=line.discount_percent,
            tax_rate=tax_rate,
        )
        calculated_lines.append(amounts)
        new_lines.append(
            NewInvoiceLine(
                item_id=item.id,
                description=description,
                quantity=line.quantity,
                unit_price=line.unit_price,
                discount_percent=line.discount_percent,
                tax_rate=tax_rate,
                subtotal=amounts.subtotal,
                tax=amounts.tax,
                total=amounts.total,
            )
        )

    totals = calculate_invoice_totals(calculated_lines)
    invoice = repository.create_draft(
        contact_id=contact.id,
        issue_date=payload.issue_date,
        due_date=payload.due_date,
        currency=payload.currency,
        lines=new_lines,
        subtotal=totals.subtotal,
        tax_total=totals.tax_total,
        total=totals.total,
    )

    response_body = InvoiceRead.model_validate(invoice).model_dump(mode="json")
    repository.add_idempotency_key(
        key=key,
        request_hash=request_hash,
        response_body=response_body,
    )

    try:
        repository.commit()
    except IntegrityError:
        # Otra petición concurrente pudo insertar la misma Key. La transacción
        # de esta petición se revierte y se devuelve la respuesta ganadora.
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


@router.post("/{invoice_id}/issue", response_model=InvoiceRead)
def issue_invoice(
    invoice_id: UUID,
    repository: InvoiceRepositoryDep,
) -> InvoiceRead:
    """Emite una factura DRAFT y le asigna número."""
    invoice = repository.issue(invoice_id)
    return InvoiceRead.model_validate(invoice)


@router.post("/{invoice_id}/void", response_model=InvoiceRead)
def void_invoice(
    invoice_id: UUID,
    payload: VoidInvoiceRequest,
    repository: InvoiceRepositoryDep,
) -> InvoiceRead:
    """Anula una factura emitida que no tenga pagos."""
    invoice = repository.void_invoice(invoice_id, payload.reason)
    return InvoiceRead.model_validate(invoice)


@router.get("/{invoice_id}", response_model=InvoiceRead)
def get_invoice(
    invoice_id: UUID,
    repository: InvoiceRepositoryDep,
) -> InvoiceRead:
    """Obtiene una factura con sus líneas."""
    invoice = repository.get_by_id(invoice_id)
    if invoice is None:
        raise ResourceNotFoundError("Factura no encontrada")
    return InvoiceRead.model_validate(invoice)


@router.get("", response_model=list[InvoiceRead])
def list_invoices(
    repository: InvoiceRepositoryDep,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[InvoiceRead]:
    """Lista facturas con paginación por offset."""
    invoices = repository.list(limit=limit, offset=offset)
    return [InvoiceRead.model_validate(invoice) for invoice in invoices]


@router.delete("/{invoice_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_invoice(
    invoice_id: UUID,
    repository: InvoiceRepositoryDep,
) -> Response:
    """Elimina una factura únicamente si está en DRAFT."""
    repository.delete_draft(invoice_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
