"""Repositorio de impuestos con SQLAlchemy 2."""

from __future__ import annotations

from typing import Any, cast
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.engine import CursorResult
from sqlalchemy.orm import Session

from app.domain.exceptions import ResourceNotFoundError, VersionConflictError
from app.domain.models.tax import Tax


class TaxRepository:
    """Acceso a datos de impuestos; excluye soft-deleted por defecto."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, values: dict[str, Any]) -> Tax:
        tax = Tax(**values)
        self.db.add(tax)
        self.db.commit()
        self.db.refresh(tax)
        return tax

    def get_by_id(self, tax_id: UUID) -> Tax | None:
        statement = select(Tax).where(
            Tax.id == tax_id,
            Tax.deleted_at.is_(None),
        )
        return self.db.scalar(statement)

    def list(self, limit: int, offset: int) -> list[Tax]:
        statement = (
            select(Tax)
            .where(Tax.deleted_at.is_(None))
            .order_by(Tax.created_at.desc(), Tax.id)
            .limit(limit)
            .offset(offset)
        )
        return list(self.db.scalars(statement).all())

    def update(
        self,
        tax_id: UUID,
        expected_version: int,
        values: dict[str, Any],
    ) -> Tax:
        statement = (
            update(Tax)
            .where(
                Tax.id == tax_id,
                Tax.version == expected_version,
                Tax.deleted_at.is_(None),
            )
            .values(
                **values,
                version=Tax.version + 1,
                updated_at=func.now(),
            )
        )
        result = cast(CursorResult[Any], self.db.execute(statement))

        if result.rowcount == 0:
            self._raise_update_error(tax_id)

        self.db.commit()
        updated = self.get_by_id(tax_id)
        if updated is None:
            raise ResourceNotFoundError("Impuesto no encontrado")
        return updated

    def soft_delete(self, tax_id: UUID) -> None:
        statement = (
            update(Tax)
            .where(Tax.id == tax_id, Tax.deleted_at.is_(None))
            .values(
                deleted_at=func.now(),
                updated_at=func.now(),
                version=Tax.version + 1,
            )
        )
        result = cast(CursorResult[Any], self.db.execute(statement))

        if result.rowcount == 0:
            raise ResourceNotFoundError("Impuesto no encontrado")

        self.db.commit()

    def _raise_update_error(self, tax_id: UUID) -> None:
        exists = self.db.scalar(
            select(Tax.id).where(
                Tax.id == tax_id,
                Tax.deleted_at.is_(None),
            )
        )
        if exists is None:
            raise ResourceNotFoundError("Impuesto no encontrado")
        raise VersionConflictError("La versión del impuesto no coincide")
