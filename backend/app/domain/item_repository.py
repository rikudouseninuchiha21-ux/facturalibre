"""Repositorio de ítems con SQLAlchemy 2."""

from __future__ import annotations

from typing import Any, cast
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.engine import CursorResult
from sqlalchemy.orm import Session

from app.domain.exceptions import ResourceNotFoundError, VersionConflictError
from app.domain.models.item import Item


class ItemRepository:
    """Acceso a datos de ítems; excluye soft-deleted por defecto."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, values: dict[str, Any]) -> Item:
        item = Item(**values)
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        return item

    def get_by_id(self, item_id: UUID) -> Item | None:
        statement = select(Item).where(
            Item.id == item_id,
            Item.deleted_at.is_(None),
        )
        return self.db.scalar(statement)

    def list(self, limit: int, offset: int) -> list[Item]:
        statement = (
            select(Item)
            .where(Item.deleted_at.is_(None))
            .order_by(Item.created_at.desc(), Item.id)
            .limit(limit)
            .offset(offset)
        )
        return list(self.db.scalars(statement).all())

    def update(
        self,
        item_id: UUID,
        expected_version: int,
        values: dict[str, Any],
    ) -> Item:
        statement = (
            update(Item)
            .where(
                Item.id == item_id,
                Item.version == expected_version,
                Item.deleted_at.is_(None),
            )
            .values(
                **values,
                version=Item.version + 1,
                updated_at=func.now(),
            )
        )
        result = cast(CursorResult[Any], self.db.execute(statement))

        if result.rowcount == 0:
            self._raise_update_error(item_id)

        self.db.commit()
        updated = self.get_by_id(item_id)
        if updated is None:
            raise ResourceNotFoundError("Ítem no encontrado")
        return updated

    def soft_delete(self, item_id: UUID) -> None:
        statement = (
            update(Item)
            .where(Item.id == item_id, Item.deleted_at.is_(None))
            .values(
                deleted_at=func.now(),
                updated_at=func.now(),
                version=Item.version + 1,
            )
        )
        result = cast(CursorResult[Any], self.db.execute(statement))

        if result.rowcount == 0:
            raise ResourceNotFoundError("Ítem no encontrado")

        self.db.commit()

    def _raise_update_error(self, item_id: UUID) -> None:
        exists = self.db.scalar(
            select(Item.id).where(
                Item.id == item_id,
                Item.deleted_at.is_(None),
            )
        )
        if exists is None:
            raise ResourceNotFoundError("Ítem no encontrado")
        raise VersionConflictError("La versión del ítem no coincide")
