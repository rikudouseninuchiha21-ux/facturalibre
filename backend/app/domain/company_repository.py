"""Acceso a empresas y membresías de usuario."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.models.auth import User, UserRole
from app.domain.models.company import Company, UserCompany
from app.domain.models.company_setting import CompanySetting


@dataclass(frozen=True)
class CompanyMembership:
    """Empresa y rol del usuario dentro de ella."""

    company: Company
    role: UserRole


class CompanyRepository:
    """Consultas y altas de empresas y accesos."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def list_for_user(self, user_id: UUID) -> list[CompanyMembership]:
        """Empresas accesibles por el usuario, ordenadas por antigüedad."""
        statement = (
            select(Company, UserCompany.role)
            .join(UserCompany, UserCompany.company_id == Company.id)
            .where(UserCompany.user_id == user_id)
            .order_by(Company.created_at, Company.id)
        )
        return [
            CompanyMembership(company=company, role=role)
            for company, role in self.db.execute(statement).all()
        ]

    def get_for_user(self, user_id: UUID, company_id: UUID) -> CompanyMembership | None:
        """Membresía concreta del usuario, o ``None`` si no tiene acceso."""
        statement = (
            select(Company, UserCompany.role)
            .join(UserCompany, UserCompany.company_id == Company.id)
            .where(UserCompany.user_id == user_id, Company.id == company_id)
        )
        row = self.db.execute(statement).first()
        if row is None:
            return None
        return CompanyMembership(company=row[0], role=row[1])

    def get_membership(self, user_id: UUID, company_id: UUID) -> UserCompany | None:
        """Fila de acceso pura, útil para validaciones de rol."""
        return self.db.scalar(
            select(UserCompany).where(
                UserCompany.user_id == user_id,
                UserCompany.company_id == company_id,
            )
        )

    def get_by_id(self, company_id: UUID) -> Company | None:
        """Busca una empresa por id."""
        return self.db.scalar(select(Company).where(Company.id == company_id))

    def get_default(self) -> Company | None:
        """Empresa histórica: la más antigua del sistema."""
        return self.db.scalar(select(Company).order_by(Company.created_at, Company.id).limit(1))

    def ensure_default(self) -> Company:
        """Devuelve la empresa inicial y la crea si la base está vacía."""
        company = self.get_default()
        if company is not None:
            return company

        company = Company(name="Mi Empresa S.A.S.")
        self.db.add(company)
        self.db.flush()
        self.db.add(CompanySetting(company_id=company.id, name=company.name))
        self.db.flush()
        return company

    def add_membership(
        self,
        user_id: UUID,
        company_id: UUID,
        role: UserRole,
    ) -> UserCompany:
        """Crea o actualiza el acceso de un usuario a una empresa."""
        membership = self.get_membership(user_id, company_id)
        if membership is None:
            membership = UserCompany(user_id=user_id, company_id=company_id, role=role)
            self.db.add(membership)
        else:
            membership.role = role
        self.db.flush()
        return membership

    def list_company_users(self, company_id: UUID) -> list[tuple[User, UserRole]]:
        """Usuarios con acceso a una empresa y su rol en ella."""
        statement = (
            select(User, UserCompany.role)
            .join(UserCompany, UserCompany.user_id == User.id)
            .where(UserCompany.company_id == company_id)
            .order_by(User.full_name, User.email)
        )
        return list(self.db.execute(statement).all())
