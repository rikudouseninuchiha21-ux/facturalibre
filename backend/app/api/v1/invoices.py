"""Rutas de creación, emisión y consulta de facturas."""

from datetime import UTC, datetime
from decimal import Decimal
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Response, status
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.dependencies.auth import get_current_user, require_role
from app.application.accounting.service import AccountingService
from app.application.credit_note_schemas import (
    CreditNoteCreate,
    CreditNoteRead,
)
from app.application.credit_note_schemas import (
    canonical_body_hash as canonical_credit_note_hash,
)
from app.application.inventory.service import InventoryService
from app.application.invoice_schemas import (
    InvoiceCreate,
    InvoiceRead,
    VoidInvoiceRequest,
    canonical_body_hash,
)
from app.application.invoice_service import (
    apply_invoice_issue_effects,
    create_invoice_draft,
)
from app.domain.calculations import (
    LineAmounts,
    calculate_invoice_totals,
    round_money,
)
from app.domain.credit_note_repository import CreditNoteRepository, NewCreditNoteLine
from app.domain.exceptions import InventoryError, ResourceNotFoundError
from app.domain.invoice_repository import InvoiceRepository
from app.domain.models.auth import UserRole
from app.domain.models.invoice_line import InvoiceLine
from app.domain.models.stock import StockMovementType
from app.domain.warehouse_repository import WarehouseRepository
from app.infrastructure.database import get_db
from app.infrastructure.transactions import operation_transaction

router = APIRouter(
    prefix="/invoices",
    tags=["invoices"],
    dependencies=[
        Depends(get_current_user),
        Depends(require_role([UserRole.ACCOUNTANT, UserRole.ADMIN])),
    ],
)

DbSession = Annotated[Session, Depends(get_db)]
IdempotencyKeyHeader = Annotated[UUID, Header(alias="Idempotency-Key")]

IDEMPOTENCY_MISMATCH = "Idempotency-Key reutilizada con body diferente"


def get_invoice_repository(db: DbSession) -> InvoiceRepository:
    """Construye el repositorio con la sesión de la petición."""
    return InvoiceRepository(db)


InvoiceRepositoryDep = Annotated[InvoiceRepository, Depends(get_invoice_repository)]


def get_credit_note_repository(db: DbSession) -> CreditNoteRepository:
    """Construye el repositorio de notas crédito con la sesión de la petición."""
    return CreditNoteRepository(db)


CreditNoteRepositoryDep = Annotated[CreditNoteRepository, Depends(get_credit_note_repository)]


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

    invoice = create_invoice_draft(db, payload)

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
    db: DbSession,
    repository: InvoiceRepositoryDep,
) -> InvoiceRead:
    """Emite una factura, descuenta inventario y genera el asiento contable.

    Las tres operaciones comparten la misma transacción: si falta stock o falla
    la contabilidad, la factura vuelve a quedar en borrador sin movimientos.
    """
    with operation_transaction(db):
        invoice = repository.issue(invoice_id)
        apply_invoice_issue_effects(db, invoice)

    issued = repository.get_by_id(invoice_id)
    if issued is None:
        raise ResourceNotFoundError("Factura no encontrada")
    return InvoiceRead.model_validate(issued)


@router.post("/{invoice_id}/void", response_model=InvoiceRead)
def void_invoice(
    invoice_id: UUID,
    payload: VoidInvoiceRequest,
    db: DbSession,
    repository: InvoiceRepositoryDep,
) -> InvoiceRead:
    """Anula una factura y genera el contra-asiento en la misma transacción."""
    with operation_transaction(db):
        invoice = repository.void_invoice(invoice_id, payload.reason)
        AccountingService(db).record_invoice_void(invoice)

    voided = repository.get_by_id(invoice_id)
    if voided is None:
        raise ResourceNotFoundError("Factura no encontrada")
    return InvoiceRead.model_validate(voided)


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


@router.post(
    "/{invoice_id}/credit-notes",
    response_model=CreditNoteRead,
    status_code=status.HTTP_201_CREATED,
)
def create_credit_note(
    invoice_id: UUID,
    payload: CreditNoteCreate,
    idempotency_key: IdempotencyKeyHeader,
    db: DbSession,
    invoice_repository: InvoiceRepositoryDep,
    credit_note_repository: CreditNoteRepositoryDep,
) -> JSONResponse:
    """Crea una nota crédito DRAFT sobre una factura emitida aplicando idempotencia."""
    key = str(idempotency_key)
    request_hash = canonical_credit_note_hash(payload)

    existing = credit_note_repository.get_idempotency_key(key)
    if existing is not None:
        if existing.request_hash != request_hash:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=IDEMPOTENCY_MISMATCH,
            )
        if existing.response_body is not None:
            return JSONResponse(
                status_code=status.HTTP_201_CREATED,
                content=existing.response_body,
            )

    invoice = invoice_repository.get_by_id(invoice_id)
    if invoice is None:
        raise ResourceNotFoundError("Factura no encontrada")
    if invoice.lifecycle_status != "issued":
        raise HTTPException(
            status_code=422,
            detail="Solo se pueden crear notas crédito sobre facturas emitidas",
        )

    # Validar que las cantidades devueltas no excedan las originales.
    original_lines = {line.id: line for line in invoice.lines}
    calculated_lines: list[LineAmounts] = []
    new_lines: list[NewCreditNoteLine] = []

    for line in payload.lines:
        line_subtotal = round_money(line.quantity * line.unit_price)
        line_tax = round_money(line_subtotal * line.tax_rate / Decimal("100"))
        line_total = round_money(line_subtotal + line_tax)

        if line.invoice_line_id is not None:
            original_line = original_lines.get(line.invoice_line_id)
            if original_line is None:
                raise HTTPException(
                    status_code=422,
                    detail=f"invoice_line_id {line.invoice_line_id} no pertenece a esta factura",
                )
            if line.quantity > original_line.quantity:
                raise HTTPException(
                    status_code=422,
                    detail=(
                        f"La cantidad devuelta ({line.quantity}) excede la cantidad "
                        f"original ({original_line.quantity})"
                    ),
                )

        calculated_lines.append(
            LineAmounts(
                subtotal=line_subtotal,
                tax=line_tax,
                total=line_total,
            )
        )
        new_lines.append(
            NewCreditNoteLine(
                invoice_line_id=line.invoice_line_id,
                description=line.description,
                quantity=line.quantity,
                unit_price=line.unit_price,
                tax_rate=line.tax_rate,
                line_subtotal=line_subtotal,
                line_tax=line_tax,
                line_total=line_total,
            )
        )

    totals = calculate_invoice_totals(calculated_lines)
    credit_note = credit_note_repository.create_draft(
        invoice_id=invoice.id,
        issue_date=payload.issue_date,
        lines=new_lines,
        subtotal=totals.subtotal,
        tax_total=totals.tax_total,
        total=totals.total,
    )

    response_body = CreditNoteRead.model_validate(credit_note).model_dump(mode="json")
    credit_note_repository.add_idempotency_key(
        key=key,
        request_hash=request_hash,
        response_body=response_body,
    )

    try:
        credit_note_repository.commit()
    except IntegrityError:
        credit_note_repository.rollback()
        winner = credit_note_repository.get_idempotency_key(key)
        if winner is None:
            raise
        if winner.request_hash != request_hash:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=IDEMPOTENCY_MISMATCH,
            ) from None
        if winner.response_body is not None:
            return JSONResponse(
                status_code=status.HTTP_201_CREATED,
                content=winner.response_body,
            )

    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content=response_body,
    )


@router.post(
    "/{invoice_id}/credit-notes/{credit_note_id}/issue",
    response_model=CreditNoteRead,
)
def issue_credit_note(
    invoice_id: UUID,
    credit_note_id: UUID,
    db: DbSession,
    invoice_repository: InvoiceRepositoryDep,
    credit_note_repository: CreditNoteRepositoryDep,
) -> CreditNoteRead:
    """Emite una nota crédito DRAFT, devuelve stock y genera el asiento contable."""

    with operation_transaction(db):
        credit_note = credit_note_repository.issue(credit_note_id)
        if credit_note.invoice_id != invoice_id:
            raise ResourceNotFoundError("Nota crédito no pertenece a esta factura")

        # Inventario: devolver stock de los ítems devueltos a la bodega PRINCIPAL.
        warehouse_id = WarehouseRepository(db).get_default_active_id()
        if warehouse_id is None:
            raise InventoryError("No hay una bodega activa configurada para notas crédito")
        for line in credit_note.lines:
            # Obtener el item_id de la línea de factura original si está vinculada.
            resolved_item_id: UUID | None = None
            if line.invoice_line_id is not None:
                invoice_line = db.get(InvoiceLine, line.invoice_line_id)
                if invoice_line is not None:
                    resolved_item_id = invoice_line.item_id
            if resolved_item_id is None:
                continue
            InventoryService(db).register_movement(
                item_id=resolved_item_id,
                warehouse_id=warehouse_id,
                movement_type=StockMovementType.IN,
                quantity=line.quantity,
                unit_cost=None,
                reference=credit_note.number or str(credit_note.id),
            )

        # Contabilidad: asiento de nota crédito.
        AccountingService(db).record_credit_note_issued(credit_note)

        # Actualizar balance de la factura original.
        invoice = invoice_repository.get_by_id(invoice_id)
        if invoice is None:
            raise ResourceNotFoundError("Factura no encontrada")
        invoice.balance = round_money(invoice.balance - credit_note.total)
        invoice.version += 1
        invoice.updated_at = datetime.now(UTC)

    issued = credit_note_repository.get_by_id(credit_note_id)
    if issued is None:
        raise ResourceNotFoundError("Nota crédito no encontrada")
    return CreditNoteRead.model_validate(issued)


@router.get(
    "/{invoice_id}/credit-notes",
    response_model=list[CreditNoteRead],
)
def list_credit_notes(
    invoice_id: UUID,
    invoice_repository: InvoiceRepositoryDep,
    credit_note_repository: CreditNoteRepositoryDep,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[CreditNoteRead]:
    """Lista las notas crédito de una factura."""
    invoice = invoice_repository.get_by_id(invoice_id)
    if invoice is None:
        raise ResourceNotFoundError("Factura no encontrada")
    credit_notes = credit_note_repository.list_by_invoice(invoice_id, limit=limit, offset=offset)
    return [CreditNoteRead.model_validate(cn) for cn in credit_notes]
