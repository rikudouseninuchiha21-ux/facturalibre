"""Casos de uso de empresas y membresías."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from app.application.company_schemas import CompanyCreate
from app.domain.company_repository import CompanyMembership, CompanyRepository
from app.domain.crm_defaults import seed_default_stages
from app.domain.exceptions import ResourceNotFoundError
from app.domain.models.auth import User, UserRole
from app.domain.models.company import Company, UserCompany
from app.domain.models.company_setting import CompanySetting
from app.infrastructure.transactions import operation_transaction


class CompanyService:
    """Altas de empresas, configuración inicial y accesos."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.repository = CompanyRepository(db)

    def create(self, payload: CompanyCreate, creator_id: UUID) -> Company:
        """Crea una empresa, su configuración y la membresía del creador."""
        with operation_transaction(self.db):
            company = Company(
                name=payload.name,
                tax_id=payload.tax_id,
                dv=payload.dv,
                address=payload.address,
                phone=payload.phone,
                email=str(payload.email) if payload.email is not None else None,
                tax_regime=payload.tax_regime,
                person_type=payload.person_type,
                fiscal_responsibility=payload.fiscal_responsibility,
                dian_municipality_code=payload.dian_municipality_code,
                dian_department_code=payload.dian_department_code,
            )
            self.db.add(company)
            self.db.flush()
            seed_default_stages(self.db, company.id)

            self.repository.add_membership(creator_id, company.id, UserRole.ADMIN)
            self.db.add(
                CompanySetting(
                    company_id=company.id,
                    name=payload.name,
                    tax_id=payload.tax_id,
                    dv=payload.dv,
                    address=payload.address,
                    phone=payload.phone,
                    email=str(payload.email) if payload.email is not None else None,
                    tax_regime=payload.tax_regime,
                    person_type=payload.person_type,
                    fiscal_responsibility=payload.fiscal_responsibility,
                    dian_municipality_code=payload.dian_municipality_code,
                    dian_department_code=payload.dian_department_code,
                )
            )
            self.db.flush()
            return company

    def list_for_user(self, user_id: UUID) -> list[CompanyMembership]:
        """Empresas a las que el usuario tiene acceso."""
        return self.repository.list_for_user(user_id)

    def get_for_user(self, user_id: UUID, company_id: UUID) -> CompanyMembership | None:
        """Membresía del usuario en una empresa."""
        return self.repository.get_for_user(user_id, company_id)

    def assign_user(
        self,
        *,
        actor_id: UUID,
        company_id: UUID,
        user_id: UUID,
        role: UserRole,
    ) -> tuple[User, UserCompany]:
        """Asigna un usuario a una empresa validando el rol del actor."""
        with operation_transaction(self.db):
            actor_membership = self.repository.get_for_user(actor_id, company_id)
            if actor_membership is None or actor_membership.role is not UserRole.ADMIN:
                raise PermissionError("Se requiere rol ADMIN en esta empresa")

            user = self.db.get(User, user_id)
            if user is None:
                raise ResourceNotFoundError("Usuario no encontrado")

            membership = self.repository.add_membership(user_id, company_id, role)
            return user, membership

    def list_company_users(self, company_id: UUID) -> list[tuple[User, UserRole]]:
        """Miembros de una empresa con su rol."""
        return self.repository.list_company_users(company_id)
