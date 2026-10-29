"""Administración de empresas y accesos por tenant."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.dependencies.auth import CurrentUser, get_current_user, require_role
from app.application.company_schemas import (
    CompanyCreate,
    CompanyMembershipRead,
    CompanyRead,
    CompanyUserAssign,
    CompanyUserRead,
)
from app.application.company_service import CompanyService
from app.domain.company_repository import CompanyRepository
from app.domain.exceptions import ResourceNotFoundError
from app.domain.models.auth import UserRole
from app.infrastructure.database import get_db

router = APIRouter(
    prefix="/companies",
    tags=["companies"],
    dependencies=[Depends(get_current_user)],
)

DbSession = Annotated[Session, Depends(get_db)]


def get_company_service(db: DbSession) -> CompanyService:
    """Construye el servicio de empresas."""
    return CompanyService(db)


CompanyServiceDep = Annotated[CompanyService, Depends(get_company_service)]


def _ensure_company_admin(db: Session, user_id: UUID, company_id: UUID) -> None:
    """Exige rol ADMIN dentro de la empresa indicada."""
    membership = CompanyRepository(db).get_for_user(user_id, company_id)
    if membership is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tiene acceso a esta empresa",
        )
    if membership.role is not UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Se requiere rol ADMIN en esta empresa",
        )


@router.get("", response_model=list[CompanyMembershipRead])
def list_companies(
    current_user: CurrentUser,
    service: CompanyServiceDep,
) -> list[CompanyMembershipRead]:
    """Lista las empresas a las que el usuario tiene acceso."""
    return [
        CompanyMembershipRead(
            company=CompanyRead.model_validate(item.company),
            role=item.role,
        )
        for item in service.list_for_user(current_user.id)
    ]


@router.post(
    "",
    response_model=CompanyRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_role([UserRole.ADMIN]))],
)
def create_company(
    payload: CompanyCreate,
    current_user: CurrentUser,
    service: CompanyServiceDep,
) -> CompanyRead:
    """Crea una empresa y asigna al creador como ADMIN."""
    try:
        company = service.create(payload, current_user.id)
    except IntegrityError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe una empresa con ese NIT",
        ) from exc
    return CompanyRead.model_validate(company)


@router.get("/{company_id}/users", response_model=list[CompanyUserRead])
def list_company_users(
    company_id: UUID,
    current_user: CurrentUser,
    db: DbSession,
    service: CompanyServiceDep,
) -> list[CompanyUserRead]:
    """Lista los usuarios con acceso a una empresa."""
    _ensure_company_admin(db, current_user.id, company_id)
    return [
        CompanyUserRead(
            user_id=user.id,
            email=user.email,
            full_name=user.full_name,
            role=role,
            is_active=user.is_active,
        )
        for user, role in service.list_company_users(company_id)
    ]


@router.post(
    "/{company_id}/users",
    response_model=CompanyUserRead,
    status_code=status.HTTP_201_CREATED,
)
def assign_company_user(
    company_id: UUID,
    payload: CompanyUserAssign,
    current_user: CurrentUser,
    service: CompanyServiceDep,
) -> CompanyUserRead:
    """Asigna un usuario existente a una empresa con un rol."""
    try:
        user, membership = service.assign_user(
            actor_id=current_user.id,
            company_id=company_id,
            user_id=payload.user_id,
            role=payload.role,
        )
    except PermissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc
    except ResourceNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except IntegrityError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No se pudo asignar el usuario",
        ) from exc

    return CompanyUserRead(
        user_id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=membership.role,
        is_active=user.is_active,
    )
