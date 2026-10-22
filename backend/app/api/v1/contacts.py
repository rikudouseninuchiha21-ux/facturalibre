"""Rutas CRUD para contactos."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.application.contact_schemas import ContactCreate, ContactRead, ContactUpdate
from app.domain.contact_repository import ContactRepository
from app.domain.exceptions import ResourceNotFoundError
from app.infrastructure.database import get_db

router = APIRouter(prefix="/contacts", tags=["contacts"])

DbSession = Annotated[Session, Depends(get_db)]


def get_contact_repository(db: DbSession) -> ContactRepository:
    """Construye el repositorio con la sesión de la petición."""
    return ContactRepository(db)


ContactRepositoryDep = Annotated[ContactRepository, Depends(get_contact_repository)]


@router.post("", response_model=ContactRead, status_code=status.HTTP_201_CREATED)
def create_contact(
    payload: ContactCreate,
    repository: ContactRepositoryDep,
) -> ContactRead:
    """Crea un contacto activo."""
    contact = repository.create(payload.model_dump())
    return ContactRead.model_validate(contact)


@router.get("", response_model=list[ContactRead])
def list_contacts(
    repository: ContactRepositoryDep,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[ContactRead]:
    """Lista contactos activos con paginación por offset."""
    contacts = repository.list(limit=limit, offset=offset)
    return [ContactRead.model_validate(contact) for contact in contacts]


@router.get("/{contact_id}", response_model=ContactRead)
def get_contact(
    contact_id: UUID,
    repository: ContactRepositoryDep,
) -> ContactRead:
    """Obtiene un contacto activo por id."""
    contact = repository.get_by_id(contact_id)
    if contact is None:
        raise ResourceNotFoundError("Contacto no encontrado")
    return ContactRead.model_validate(contact)


@router.patch("/{contact_id}", response_model=ContactRead)
def update_contact(
    contact_id: UUID,
    payload: ContactUpdate,
    repository: ContactRepositoryDep,
) -> ContactRead:
    """Actualiza un contacto con bloqueo optimista."""
    values = payload.model_dump(exclude_unset=True, exclude={"version"})
    contact = repository.update(
        contact_id=contact_id,
        expected_version=payload.version,
        values=values,
    )
    return ContactRead.model_validate(contact)


@router.delete("/{contact_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_contact(
    contact_id: UUID,
    repository: ContactRepositoryDep,
) -> Response:
    """Hace soft delete de un contacto."""
    repository.soft_delete(contact_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
