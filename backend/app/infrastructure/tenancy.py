"""Aislamiento multi-empresa a nivel de sesión de SQLAlchemy.

La empresa activa se guarda en ``Session.info['company_id']``. Un listener
global aplica ``with_loader_criteria`` a todas las entidades que heredan de
``CompanyScopedMixin``, de modo que SELECT, UPDATE y DELETE quedan acotados al
tenant aunque el repositorio no repita el filtro. Otro listener asigna la
empresa a las filas nuevas y rechaza modificaciones de filas ajenas.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import event
from sqlalchemy.orm import Session, with_loader_criteria

from app.domain.models.tenancy import CompanyScopedMixin

COMPANY_INFO_KEY = "company_id"


def get_company_id(db: Session) -> UUID | None:
    """Empresa activa de la sesión, o ``None`` si no hay contexto."""
    return db.info.get(COMPANY_INFO_KEY)


def set_company_id(db: Session, company_id: UUID | None) -> None:
    """Fija la empresa activa para las siguientes operaciones de la sesión."""
    db.info[COMPANY_INFO_KEY] = company_id


def require_company_id(db: Session) -> UUID:
    """Exige un contexto de empresa para operaciones Core fuera del ORM."""
    company_id = get_company_id(db)
    if company_id is None:
        raise RuntimeError("No hay empresa activa en la sesión")
    return company_id


@event.listens_for(Session, "do_orm_execute")
def _apply_tenant_filter(execute_state: object) -> None:
    """Añade el filtro de empresa a toda consulta ORM de una entidad scoped."""
    session = execute_state.session  # type: ignore[attr-defined]
    company_id = session.info.get(COMPANY_INFO_KEY)
    if company_id is None:
        return

    is_tenant_statement = (
        execute_state.is_select  # type: ignore[attr-defined]
        or execute_state.is_update  # type: ignore[attr-defined]
        or execute_state.is_delete  # type: ignore[attr-defined]
    )
    if not is_tenant_statement:
        return

    execute_state.statement = execute_state.statement.options(  # type: ignore[attr-defined]
        with_loader_criteria(
            CompanyScopedMixin,
            lambda cls: cls.company_id == company_id,
            include_aliases=True,
        )
    )


@event.listens_for(Session, "before_flush")
def _stamp_and_guard_tenant(session: Session, flush_context: object, instances: object) -> None:
    """Asigna company_id a filas nuevas y protege filas de otros tenants."""
    company_id = session.info.get(COMPANY_INFO_KEY)

    for obj in session.new:
        if not isinstance(obj, CompanyScopedMixin):
            continue
        current = getattr(obj, "company_id", None)
        if current is None:
            if company_id is None:
                raise RuntimeError(f"{type(obj).__name__} requiere company_id o una empresa activa")
            obj.company_id = company_id

    if company_id is None:
        return

    for obj in session.dirty:
        if isinstance(obj, CompanyScopedMixin) and getattr(obj, "company_id", None) != company_id:
            raise RuntimeError("Intento de modificar datos de otra empresa")

    for obj in session.deleted:
        if isinstance(obj, CompanyScopedMixin) and getattr(obj, "company_id", None) != company_id:
            raise RuntimeError("Intento de eliminar datos de otra empresa")


__all__ = [
    "COMPANY_INFO_KEY",
    "get_company_id",
    "require_company_id",
    "set_company_id",
]
