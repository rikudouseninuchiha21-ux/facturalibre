"""Endpoints del punto de venta (POS)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.dependencies.auth import get_current_user, require_role
from app.domain.models.auth import UserRole
from app.domain.models.item import Item
from app.domain.models.stock import StockBalance
from app.domain.models.tax import Tax
from app.domain.models.warehouse import Warehouse
from app.infrastructure.database import get_db

router = APIRouter(
    prefix="/pos",
    tags=["pos"],
    dependencies=[
        Depends(get_current_user),
        Depends(require_role([UserRole.CASHIER, UserRole.ADMIN])),
    ],
)

DbSession = Annotated[Session, Depends(get_db)]

MAX_RESULTS = 10


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
