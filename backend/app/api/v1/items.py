"""Rutas CRUD para ítems."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.application.item_schemas import ItemCreate, ItemRead, ItemUpdate
from app.domain.exceptions import ResourceNotFoundError
from app.domain.item_repository import ItemRepository
from app.domain.tax_repository import TaxRepository
from app.infrastructure.database import get_db

router = APIRouter(prefix="/items", tags=["items"])

DbSession = Annotated[Session, Depends(get_db)]


def get_item_repository(db: DbSession) -> ItemRepository:
    """Construye el repositorio con la sesión de la petición."""
    return ItemRepository(db)


ItemRepositoryDep = Annotated[ItemRepository, Depends(get_item_repository)]


def _validate_tax_id(tax_id: UUID | None, db: Session) -> None:
    """Comprueba que un impuesto referenciado exista y esté activo."""
    if tax_id is not None and TaxRepository(db).get_by_id(tax_id) is None:
        raise HTTPException(
            status_code=422,
            detail="tax_id no existe o está eliminado",
        )


@router.post("", response_model=ItemRead, status_code=status.HTTP_201_CREATED)
def create_item(
    payload: ItemCreate,
    db: DbSession,
    repository: ItemRepositoryDep,
) -> ItemRead:
    """Crea un ítem activo."""
    _validate_tax_id(payload.tax_id, db)
    item = repository.create(payload.model_dump())
    return ItemRead.model_validate(item)


@router.get("", response_model=list[ItemRead])
def list_items(
    repository: ItemRepositoryDep,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[ItemRead]:
    """Lista ítems activos con paginación por offset."""
    items = repository.list(limit=limit, offset=offset)
    return [ItemRead.model_validate(item) for item in items]


@router.get("/{item_id}", response_model=ItemRead)
def get_item(
    item_id: UUID,
    repository: ItemRepositoryDep,
) -> ItemRead:
    """Obtiene un ítem activo por id."""
    item = repository.get_by_id(item_id)
    if item is None:
        raise ResourceNotFoundError("Ítem no encontrado")
    return ItemRead.model_validate(item)


@router.patch("/{item_id}", response_model=ItemRead)
def update_item(
    item_id: UUID,
    payload: ItemUpdate,
    db: DbSession,
    repository: ItemRepositoryDep,
) -> ItemRead:
    """Actualiza un ítem con bloqueo optimista."""
    values = payload.model_dump(exclude_unset=True, exclude={"version"})
    if "tax_id" in values:
        _validate_tax_id(values["tax_id"], db)
    item = repository.update(
        item_id=item_id,
        expected_version=payload.version,
        values=values,
    )
    return ItemRead.model_validate(item)


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_item(
    item_id: UUID,
    repository: ItemRepositoryDep,
) -> Response:
    """Hace soft delete de un ítem."""
    repository.soft_delete(item_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
