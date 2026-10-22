"""Rutas CRUD para empleados."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.application.payroll.schemas import EmployeeCreate, EmployeeRead, EmployeeUpdate
from app.domain.employee_repository import EmployeeRepository
from app.domain.exceptions import ResourceNotFoundError
from app.infrastructure.database import get_db

router = APIRouter(prefix="/employees", tags=["employees"])

DbSession = Annotated[Session, Depends(get_db)]
EMPLOYEE_DOCUMENT_CONFLICT = "El documento del empleado ya existe"


def get_employee_repository(db: DbSession) -> EmployeeRepository:
    """Construye el repositorio con la sesión de la petición."""
    return EmployeeRepository(db)


EmployeeRepositoryDep = Annotated[EmployeeRepository, Depends(get_employee_repository)]


@router.post("", response_model=EmployeeRead, status_code=status.HTTP_201_CREATED)
def create_employee(
    payload: EmployeeCreate,
    repository: EmployeeRepositoryDep,
) -> EmployeeRead:
    """Crea un empleado."""
    try:
        employee = repository.create(payload.model_dump())
    except IntegrityError:
        repository.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=EMPLOYEE_DOCUMENT_CONFLICT,
        ) from None
    return EmployeeRead.model_validate(employee)


@router.get("", response_model=list[EmployeeRead])
def list_employees(
    repository: EmployeeRepositoryDep,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
    is_active: bool | None = None,
) -> list[EmployeeRead]:
    """Lista empleados, opcionalmente filtrados por estado."""
    employees = repository.list_employees(limit=limit, offset=offset, is_active=is_active)
    return [EmployeeRead.model_validate(employee) for employee in employees]


@router.get("/{employee_id}", response_model=EmployeeRead)
def get_employee(
    employee_id: UUID,
    repository: EmployeeRepositoryDep,
) -> EmployeeRead:
    """Obtiene un empleado por id."""
    employee = repository.get_by_id(employee_id)
    if employee is None:
        raise ResourceNotFoundError("Empleado no encontrado")
    return EmployeeRead.model_validate(employee)


@router.patch("/{employee_id}", response_model=EmployeeRead)
def update_employee(
    employee_id: UUID,
    payload: EmployeeUpdate,
    repository: EmployeeRepositoryDep,
) -> EmployeeRead:
    """Actualiza los datos editables de un empleado."""
    values = payload.model_dump(exclude_unset=True)
    try:
        employee = repository.update(employee_id, values)
    except IntegrityError:
        repository.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=EMPLOYEE_DOCUMENT_CONFLICT,
        ) from None
    return EmployeeRead.model_validate(employee)


@router.delete("/{employee_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_employee(
    employee_id: UUID,
    repository: EmployeeRepositoryDep,
) -> Response:
    """Desactiva al empleado sin borrar su historial de nómina."""
    repository.deactivate(employee_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
