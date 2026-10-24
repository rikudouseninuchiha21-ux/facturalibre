"""Rutas de creación, emisión y consulta de facturas de compra."""

from __future__ import annotations

from decimal import Decimal
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Response, status
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.dependencies.auth import get_current_user
from app.application.accounting.service import AccountingService
from app.application.inventory.service import InventoryService
from app.application.purchase_schemas import (
    PurchaseCreate,
    PurchaseRead,
    canonical_body_hash,
)
from app.domain.calculations import (
    calculate_invoice_totals,
    round_money,
)
from app.domain.contact_repository import ContactRepository
from app.domain.exceptions import InventoryError, ResourceNotFoundError
from app.domain.item_repository import ItemRepository
from app.domain.models.purchase import PurchaseStatus
from app.domain.models.stock import StockMovementType
from app.domain.purchase_repository import (
    NewPurchaseLine,
    PurchaseRepository,
)
from app.domain.warehouse_repository import WarehouseRepository
from app.infrastructure.database import get_db
from app.infrastructure.transactions import operation_transaction

router = APIRouter(
    prefix="/purchases",
    tags=["purchases"],
    dependencies=[Depends(get_current_user)],
)

DbSession = Annotated[Session, Depends(get_db)]
IdempotencyKeyHeader = Annotated[UUID, Header(alias="Idempotency-Key")]

IDEMPOTENCY_MISMATCH = "Idempotency-Key reutilizada con body diferente"


def get_purchase_repository(db: DbSession) -> PurchaseRepository:
    """Construye el repositorio con la sesión de la petición."""
    return PurchaseRepository(db)


PurchaseRepositoryDep = Annotated[PurchaseRepository, Depends(get_purchase_repository)]


@router.post("", response_model=PurchaseRead, status_code=status.HTTP_201_CREATED)
def create_purchase(
    payload: PurchaseCreate,
    idempotency_key: IdempotencyKeyHeader,
    db: DbSession,
    repository: PurchaseRepositoryDep,
) -> JSONResponse:
    """Crea una factura de compra DRAFT aplicando idempotencia por body."""
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

    contact = ContactRepository(db).get_by_id(payload.supplier_id)
    if contact is None:
        raise HTTPException(
            status_code=422,
            detail="supplier_id no existe o está eliminado",
        )

    item_repository = ItemRepository(db)
    calculated_lines = []
    new_lines: list[NewPurchaseLine] = []

    for line in payload.lines:
        if line.item_id is not None:
            item = item_repository.get_by_id(line.item_id)
            if item is None:
                raise HTTPException(
                    status_code=422,
                    detail=f"item_id {line.item_id} no existe o está eliminado",
                )

        # REQUIERE VALIDACIÓN: contador/experto DIAN. La tarifa de impuesto de
        # compra debe alinearse con el catálogo tributario oficial.
        tax_rate = line.tax_rate

        description = line.description
        line_subtotal = round_money(line.quantity * line.unit_cost)
        line_tax = round_money(line_subtotal * tax_rate / Decimal("100"))
        line_total = round_money(line_subtotal + line_tax)

        calculated_lines.append(
            type(
                "LineAmounts",
                (),
                {
                    "subtotal": line_subtotal,
                    "tax": line_tax,
                    "total": line_total,
                },
            )()
        )
        new_lines.append(
            NewPurchaseLine(
                item_id=line.item_id,
                description=description,
                quantity=line.quantity,
                unit_cost=line.unit_cost,
                tax_rate=tax_rate,
                line_subtotal=line_subtotal,
                line_tax=line_tax,
                line_total=line_total,
            )
        )

    totals = calculate_invoice_totals(calculated_lines)
    purchase = repository.create_draft(
        supplier_id=contact.id,
        issue_date=payload.issue_date,
        due_date=payload.due_date,
        lines=new_lines,
        subtotal=totals.subtotal,
        tax_total=totals.tax_total,
        total=totals.total,
    )

    response_body = PurchaseRead.model_validate(purchase).model_dump(mode="json")
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


@router.post("/{purchase_id}/issue", response_model=PurchaseRead)
def issue_purchase(
    purchase_id: UUID,
    db: DbSession,
    repository: PurchaseRepositoryDep,
) -> PurchaseRead:
    """Emite una factura de compra, sube inventario y genera el asiento contable.

    Las tres operaciones comparten la misma transacción: si falla el inventario
    o la contabilidad, la compra vuelve a quedar en borrador.
    """
    with operation_transaction(db):
        purchase = repository.issue(purchase_id)

        # Inventario: entrada de stock por cada línea en la bodega PRINCIPAL.
        warehouse_id = WarehouseRepository(db).get_default_active_id()
        if warehouse_id is None:
            raise InventoryError("No hay una bodega activa configurada para compras")
        for line in purchase.lines:
            if line.item_id is None:
                continue
            InventoryService(db).register_movement(
                item_id=line.item_id,
                warehouse_id=warehouse_id,
                movement_type=StockMovementType.IN,
                quantity=line.quantity,
                unit_cost=line.unit_cost,
                reference=purchase.number or str(purchase.id),
            )

        # Contabilidad: asiento de compra.
        AccountingService(db).record_purchase_issued(purchase)

    issued = repository.get_by_id(purchase_id)
    if issued is None:
        raise ResourceNotFoundError("Factura de compra no encontrada")
    return PurchaseRead.model_validate(issued)


@router.get("/{purchase_id}", response_model=PurchaseRead)
def get_purchase(
    purchase_id: UUID,
    repository: PurchaseRepositoryDep,
) -> PurchaseRead:
    """Obtiene una factura de compra con sus líneas."""
    purchase = repository.get_by_id(purchase_id)
    if purchase is None:
        raise ResourceNotFoundError("Factura de compra no encontrada")
    return PurchaseRead.model_validate(purchase)


@router.get("", response_model=list[PurchaseRead])
def list_purchases(
    repository: PurchaseRepositoryDep,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[PurchaseRead]:
    """Lista facturas de compra con paginación por offset."""
    purchases = repository.list(limit=limit, offset=offset)
    return [PurchaseRead.model_validate(purchase) for purchase in purchases]


@router.delete("/{purchase_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_purchase(
    purchase_id: UUID,
    repository: PurchaseRepositoryDep,
) -> Response:
    """Elimina una factura de compra únicamente si está en DRAFT."""
    from app.domain.exceptions import InvoiceStateError

    purchase = repository.get_by_id(purchase_id)
    if purchase is None:
        raise ResourceNotFoundError("Factura de compra no encontrada")
    if purchase.status is not PurchaseStatus.DRAFT:
        raise InvoiceStateError("Solo se eliminan facturas de compra en borrador")
    # Soft delete no implementado en esta fase para compras; se elimina físicamente
    # solo borradores para mantener el MVP simple.
    repository.db.delete(purchase)
    repository.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
