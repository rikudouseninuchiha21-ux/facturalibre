"""Endpoints del punto de venta (POS)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from fastapi.responses import JSONResponse
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.dependencies.auth import get_current_user, require_role
from app.application.invoice_schemas import InvoiceCreate, InvoiceRead, canonical_body_hash
from app.application.invoice_service import (
    apply_invoice_issue_effects,
    create_invoice_draft,
)
from app.application.payment_schemas import PaymentRead
from app.application.payment_service import PaymentService
from app.application.pos_schemas import PosCheckoutCreate, PosCheckoutRead
from app.domain.contact_repository import ContactRepository
from app.domain.invoice_repository import InvoiceRepository
from app.domain.models.auth import UserRole
from app.domain.models.contact import ContactStatus, ContactType
from app.domain.models.idempotency_key import IdempotencyKey
from app.domain.models.item import Item
from app.domain.models.stock import StockBalance
from app.domain.models.tax import Tax
from app.domain.models.warehouse import Warehouse
from app.domain.payment_repository import PaymentRepository
from app.infrastructure.database import get_db
from app.infrastructure.transactions import operation_transaction

router = APIRouter(
    prefix="/pos",
    tags=["pos"],
    dependencies=[
        Depends(get_current_user),
        Depends(require_role([UserRole.CASHIER, UserRole.ADMIN])),
    ],
)

DbSession = Annotated[Session, Depends(get_db)]
IdempotencyKeyHeader = Annotated[UUID, Header(alias="Idempotency-Key")]

MAX_RESULTS = 10
ZERO = Decimal("0.00")
IDEMPOTENCY_MISMATCH = "Idempotency-Key reutilizada con body diferente"
GENERIC_CUSTOMER_TAX_ID = "222222222222"
GENERIC_CUSTOMER_NAME = "Consumidor Final"


def _resolve_contact_id(db: Session, contact_id: UUID | None) -> UUID:
    """Resuelve el contacto real de una venta POS.

    Si el cajero eligió "Consumidor Final", busca el contacto genérico por NIT;
    si no existe, usa el primer contacto con estado CUSTOMER y, como última
    alternativa, lo crea dentro de la misma transacción del checkout.
    """
    if contact_id is not None:
        return contact_id

    repository = ContactRepository(db)
    contact = repository.get_by_tax_id(GENERIC_CUSTOMER_TAX_ID)
    if contact is None:
        contact = repository.get_first_by_status(ContactStatus.CUSTOMER)
    if contact is None:
        contact = repository.create_pending(
            {
                "name": GENERIC_CUSTOMER_NAME,
                "tax_id": GENERIC_CUSTOMER_TAX_ID,
                "type": ContactType.CUSTOMER,
                "status": ContactStatus.CUSTOMER,
            }
        )
    return contact.id


def _build_invoice_payload(
    db: Session,
    payload: PosCheckoutCreate,
) -> InvoiceCreate:
    """Convierte el checkout del POS en el payload de facturación normal."""
    return InvoiceCreate(
        contact_id=_resolve_contact_id(db, payload.contact_id),
        issue_date=payload.issue_date,
        due_date=payload.due_date,
        currency=payload.currency,
        lines=payload.lines,
    )


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


@router.get("/search")
def search_items(
    db: DbSession,
    q: Annotated[str, Query(min_length=1, description="Término de búsqueda por nombre")] = "",
) -> list[dict]:
    """Busca ítems activos por nombre para el punto de venta.

    Devuelve hasta 10 resultados con id, nombre, precio unitario, tasa de
    impuesto y stock actual en la bodega PRINCIPAL.
    """
    warehouse_id = db.scalar(
        select(Warehouse.id).where(
            Warehouse.is_active.is_(True),
            func.lower(Warehouse.code) == "principal",
        )
    )

    statement = (
        select(
            Item.id,
            Item.name,
            Item.unit_price,
            func.coalesce(Tax.rate, 0).label("tax_rate"),
            func.coalesce(StockBalance.quantity, 0).label("stock_current"),
        )
        .outerjoin(Tax, Item.tax_id == Tax.id)
        .outerjoin(
            StockBalance,
            (StockBalance.item_id == Item.id) & (StockBalance.warehouse_id == warehouse_id),
        )
        .where(Item.deleted_at.is_(None))
        .where(Item.name.ilike(f"%{q}%"))
        .order_by(Item.name)
        .limit(MAX_RESULTS)
    )

    rows = db.execute(statement).all()

    results: list[dict] = []
    for row in rows:
        results.append(
            {
                "id": str(row.id),
                "name": row.name,
                "unit_price": str(row.unit_price),
                "tax_rate": str(row.tax_rate),
                "stock_current": str(row.stock_current),
            }
        )

    return results


@router.post(
    "/checkout",
    response_model=PosCheckoutRead,
    status_code=status.HTTP_201_CREATED,
)
def checkout(
    payload: PosCheckoutCreate,
    idempotency_key: IdempotencyKeyHeader,
    db: DbSession,
) -> JSONResponse:
    """Cobra una venta del POS de forma atómica.

    En una sola transacción crea la factura, la emite, descuenta inventario,
    registra el COGS, contabiliza la venta, crea el pago en efectivo por el
    total y deja la factura en ``paid`` con saldo cero. Si cualquier paso falla,
    no queda factura, movimiento, pago ni asiento parcial.
    """
    key = str(idempotency_key)
    request_hash = canonical_body_hash(payload)
    repository = InvoiceRepository(db)
    response_body: dict[str, Any] | None = None

    try:
        with operation_transaction(db):
            response_body = _replay_response(
                repository.get_idempotency_key(key),
                request_hash,
            )
            if response_body is None:
                invoice_payload = _build_invoice_payload(db, payload)
                draft = create_invoice_draft(db, invoice_payload)
                invoice = repository.issue(draft.id)
                apply_invoice_issue_effects(db, invoice)

                payment = None
                if invoice.total > ZERO:
                    payment = PaymentService(db).register_payment(
                        invoice=invoice,
                        amount=invoice.total,
                        payment_date=invoice.issue_date or date.today(),
                        method="cash",
                        reference="POS",
                    )
                else:
                    # Una factura de total cero no admite un pago positivo, pero
                    # el POS sí debe dejarla cerrada como pagada.
                    PaymentRepository(db).recalculate_invoice(invoice)

                response_body = PosCheckoutRead(
                    invoice=InvoiceRead.model_validate(invoice),
                    payment=(PaymentRead.model_validate(payment) if payment is not None else None),
                ).model_dump(mode="json")
                repository.add_idempotency_key(
                    key=key,
                    request_hash=request_hash,
                    response_body=response_body,
                )
    except IntegrityError:
        # Otra petición concurrente insertó la misma Key. Su transacción ganó y
        # esta se revirtió por completo, incluidos factura, stock y pago.
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
