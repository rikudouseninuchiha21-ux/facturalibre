"""Repositorio de contactos con SQLAlchemy 2."""

from __future__ import annotations

from typing import Any, cast
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.engine import CursorResult
from sqlalchemy.orm import Session

from app.domain.exceptions import ResourceNotFoundError, VersionConflictError
from app.domain.models.contact import Contact, ContactStatus


class ContactRepository:
    """Acceso a datos de contactos; excluye soft-deleted por defecto."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, values: dict[str, Any]) -> Contact:
        contact = Contact(**values)
        self.db.add(contact)
        self.db.commit()
        self.db.refresh(contact)
        return contact

    def get_by_id(self, contact_id: UUID) -> Contact | None:
        statement = select(Contact).where(
            Contact.id == contact_id,
            Contact.deleted_at.is_(None),
        )
        return self.db.scalar(statement)

    def get_by_tax_id(self, tax_id: str) -> Contact | None:
        """Busca un contacto activo por identificación fiscal."""
        statement = (
            select(Contact)
            .where(
                Contact.tax_id == tax_id,
                Contact.deleted_at.is_(None),
            )
            .order_by(Contact.created_at, Contact.id)
            .limit(1)
        )
        return self.db.scalar(statement)

    def get_first_by_status(self, status: ContactStatus) -> Contact | None:
        """Devuelve el primer contacto activo con el estado indicado."""
        statement = (
            select(Contact)
            .where(
                Contact.status == status,
                Contact.deleted_at.is_(None),
            )
            .order_by(Contact.created_at, Contact.id)
            .limit(1)
        )
        return self.db.scalar(statement)

    def create_pending(self, values: dict[str, Any]) -> Contact:
        """Crea un contacto dentro de la transacción actual, sin commit.

        Se usa para entidades genéricas que deben revertirse junto con la
        operación de negocio que las crea, como el "Consumidor Final" del POS.
        """
        contact = Contact(**values)
        self.db.add(contact)
        self.db.flush()
        return contact

    def list(self, limit: int, offset: int) -> list[Contact]:
        statement = (
            select(Contact)
            .where(Contact.deleted_at.is_(None))
            .order_by(Contact.created_at.desc(), Contact.id)
            .limit(limit)
            .offset(offset)
        )
        return list(self.db.scalars(statement).all())

    def update(
        self,
        contact_id: UUID,
        expected_version: int,
        values: dict[str, Any],
    ) -> Contact:
        statement = (
            update(Contact)
            .where(
                Contact.id == contact_id,
                Contact.version == expected_version,
                Contact.deleted_at.is_(None),
            )
            .values(
                **values,
                version=Contact.version + 1,
                updated_at=func.now(),
            )
        )
        result = cast(CursorResult[Any], self.db.execute(statement))

        if result.rowcount == 0:
            self._raise_update_error(contact_id)

        self.db.commit()
        updated = self.get_by_id(contact_id)
        if updated is None:
            raise ResourceNotFoundError("Contacto no encontrado")
        return updated

    def soft_delete(self, contact_id: UUID) -> None:
        statement = (
            update(Contact)
            .where(Contact.id == contact_id, Contact.deleted_at.is_(None))
            .values(
                deleted_at=func.now(),
                updated_at=func.now(),
                version=Contact.version + 1,
            )
        )
        result = cast(CursorResult[Any], self.db.execute(statement))

        if result.rowcount == 0:
            raise ResourceNotFoundError("Contacto no encontrado")

        self.db.commit()

    def _raise_update_error(self, contact_id: UUID) -> None:
        exists = self.db.scalar(
            select(Contact.id).where(
                Contact.id == contact_id,
                Contact.deleted_at.is_(None),
            )
        )
        if exists is None:
            raise ResourceNotFoundError("Contacto no encontrado")
        raise VersionConflictError("La versión del contacto no coincide")
