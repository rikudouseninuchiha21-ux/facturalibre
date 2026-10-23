"""Rutas CRUD para impuestos."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.api.dependencies.auth import get_current_user
from app.application.tax_schemas import TaxCreate, TaxRead, TaxUpdate
from app.domain.exceptions import ResourceNotFoundError
from app.domain.tax_repository import TaxRepository
from app.infrastructure.database import get_db

router = APIRouter(
    prefix="/taxes",
    tags=["taxes"],
    dependencies=[Depends(get_current_user)],
)

DbSession = Annotated[Session, Depends(get_db)]


def get_tax_repository(db: DbSession) -> TaxRepository:
    """Construye el repositorio con la sesión de la petición."""
    return TaxRepository(db)


TaxRepositoryDep = Annotated[TaxRepository, Depends(get_tax_repository)]


@router.post("", response_model=TaxRead, status_code=status.HTTP_201_CREATED)
def create_tax(
    payload: TaxCreate,
    repository: TaxRepositoryDep,
) -> TaxRead:
    """Crea un impuesto activo."""
    tax = repository.create(payload.model_dump())
    return TaxRead.model_validate(tax)


@router.get("", response_model=list[TaxRead])
def list_taxes(
    repository: TaxRepositoryDep,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[TaxRead]:
    """Lista impuestos activos con paginación por offset."""
    taxes = repository.list(limit=limit, offset=offset)
    return [TaxRead.model_validate(tax) for tax in taxes]


@router.get("/{tax_id}", response_model=TaxRead)
def get_tax(
    tax_id: UUID,
    repository: TaxRepositoryDep,
) -> TaxRead:
    """Obtiene un impuesto activo por id."""
    tax = repository.get_by_id(tax_id)
    if tax is None:
        raise ResourceNotFoundError("Impuesto no encontrado")
    return TaxRead.model_validate(tax)


@router.patch("/{tax_id}", response_model=TaxRead)
def update_tax(
    tax_id: UUID,
    payload: TaxUpdate,
    repository: TaxRepositoryDep,
) -> TaxRead:
    """Actualiza un impuesto con bloqueo optimista."""
    values = payload.model_dump(exclude_unset=True, exclude={"version"})
    tax = repository.update(
        tax_id=tax_id,
        expected_version=payload.version,
        values=values,
    )
    return TaxRead.model_validate(tax)


@router.delete("/{tax_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_tax(
    tax_id: UUID,
    repository: TaxRepositoryDep,
) -> Response:
    """Hace soft delete de un impuesto."""
    repository.soft_delete(tax_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
