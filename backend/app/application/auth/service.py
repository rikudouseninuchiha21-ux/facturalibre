"""Casos de uso de autenticación con sesiones opacas revocables."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.application.auth.schemas import LoginRequest, RegisterRequest
from app.application.auth.security import (
    DUMMY_PASSWORD_HASH,
    SESSION_TTL,
    generate_session_token,
    hash_password,
    hash_session_token,
    verify_password,
)
from app.application.user_schemas import UserCreate
from app.domain.auth_repository import AuthRepository
from app.domain.company_repository import CompanyMembership, CompanyRepository
from app.domain.exceptions import (
    EmailAlreadyRegisteredError,
    InvalidCredentialsError,
    RegistrationClosedError,
)
from app.domain.models.auth import AuthSession, User, UserRole
from app.infrastructure.tenancy import get_company_id, set_company_id
from app.infrastructure.transactions import operation_transaction


@dataclass(frozen=True)
class LoginResult:
    """Resultado interno del login con la empresa activa resuelta."""

    user: User
    token: str
    expires_at: datetime
    membership: CompanyMembership


class AuthService:
    """Registro, login, logout y resolución de la sesión actual."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.repository = AuthRepository(db)
        self.companies = CompanyRepository(db)

    @staticmethod
    def _normalize_email(email: str) -> str:
        """Normaliza el email para que el UNIQUE no distinga mayúsculas."""
        return email.strip().lower()

    def register(self, payload: RegisterRequest) -> User:
        """Crea el primer usuario; luego el registro público queda cerrado."""
        email = self._normalize_email(str(payload.email))

        try:
            with operation_transaction(self.db):
                # Evita que dos primeras altas concurrentes creen dos usuarios.
                self.repository.lock_registration()

                if self.repository.get_by_email(email) is not None:
                    raise EmailAlreadyRegisteredError("El email ya está registrado")

                if self.repository.count_users() > 0:
                    raise RegistrationClosedError("El registro inicial ya fue completado")

                user = self.repository.add_user(
                    email=email,
                    hashed_password=hash_password(payload.password),
                    full_name=payload.full_name,
                    role=payload.role,
                )
                company = self.companies.ensure_default()
                self.companies.add_membership(user.id, company.id, payload.role)
                return user
        except IntegrityError as exc:
            # Carrera entre la verificación y el INSERT: gana el UNIQUE de la BD.
            raise EmailAlreadyRegisteredError("El email ya está registrado") from exc

    def login(self, payload: LoginRequest) -> LoginResult:
        """Valida credenciales y crea una sesión de 24 horas.

        La sesión guarda la empresa activa. Si el usuario todavía no tiene
        membresías (datos heredados), se le asigna la empresa histórica.
        """
        email = self._normalize_email(str(payload.email))
        now = datetime.now(UTC)

        with operation_transaction(self.db):
            user = self.repository.get_by_email(email)

            # Ejecutar bcrypt también cuando el email no existe reduce la
            # diferencia de tiempo que permitiría enumerar usuarios.
            password_hash = user.hashed_password if user is not None else DUMMY_PASSWORD_HASH
            password_matches = verify_password(payload.password, password_hash)

            if user is None or not password_matches or not user.is_active:
                raise InvalidCredentialsError("Credenciales inválidas")

            memberships = self.companies.list_for_user(user.id)
            if memberships:
                membership = memberships[0]
            else:
                company = self.companies.ensure_default()
                self.companies.add_membership(user.id, company.id, user.role)
                membership = CompanyMembership(company=company, role=user.role)

            # Rotación de sesión (Fase 39B): el login invalida las sesiones
            # anteriores del usuario para impedir Tokens Replayer/robados.
            self.repository.revoke_user_sessions(user.id)

            token = generate_session_token()
            expires_at = now + SESSION_TTL
            self.repository.add_session(
                user_id=user.id,
                token_hash=hash_session_token(token),
                expires_at=expires_at,
                active_company_id=membership.company.id,
            )
            set_company_id(self.db, membership.company.id)

        return LoginResult(
            user=user,
            token=token,
            expires_at=expires_at,
            membership=membership,
        )

    def logout(self, token: str | None) -> None:
        """Revoca la sesión si existe; el logout es idempotente."""
        if not token:
            return

        with operation_transaction(self.db):
            self.repository.delete_session(hash_session_token(token))

    def get_user_by_token(self, token: str | None) -> User | None:
        """Resuelve una sesión vigente a partir del token de la cookie."""
        if not token:
            return None
        return self.repository.get_user_by_session(hash_session_token(token))

    def get_session_by_token(self, token: str | None) -> tuple[User, AuthSession] | None:
        """Resuelve usuario y sesión para conocer la empresa activa."""
        if not token:
            return None
        return self.repository.get_session_by_token(hash_session_token(token))

    def resolve_membership(
        self,
        user: User,
        session: AuthSession,
    ) -> CompanyMembership:
        """Membresía activa de la sesión, con fallback a la empresa histórica."""
        membership = None
        if session.active_company_id is not None:
            membership = self.companies.get_for_user(user.id, session.active_company_id)

        if membership is None:
            memberships = self.companies.list_for_user(user.id)
            if memberships:
                membership = memberships[0]
            else:
                company = self.companies.ensure_default()
                self.companies.add_membership(user.id, company.id, user.role)
                membership = CompanyMembership(company=company, role=user.role)
            session.active_company_id = membership.company.id
            self.db.flush()

        return membership

    def switch_company(
        self,
        user: User,
        session: AuthSession,
        company_id: UUID,
    ) -> CompanyMembership:
        """Cambia la empresa activa si el usuario tiene acceso a ella."""
        membership = self.companies.get_for_user(user.id, company_id)
        if membership is None:
            raise PermissionError("Sin acceso a la empresa solicitada")

        self.repository.update_session_company(session, company_id)
        set_company_id(self.db, company_id)
        return membership

    def create_user(self, payload: UserCreate) -> User:
        """Crea un nuevo usuario con contraseña."""
        email = self._normalize_email(str(payload.email))

        with operation_transaction(self.db):
            if self.repository.get_by_email(email) is not None:
                raise EmailAlreadyRegisteredError("El email ya está registrado")

            user = self.repository.add_user(
                email=email,
                hashed_password=hash_password(payload.password),
                full_name=payload.full_name,
                role=payload.role,
            )
            company_id = get_company_id(self.db)
            company = (
                self.companies.get_by_id(company_id)
                if company_id is not None
                else self.companies.get_default()
            )
            if company is not None:
                self.companies.add_membership(user.id, company.id, payload.role)
            return user

    def update_user(
        self,
        user_id: UUID,
        *,
        email: str | None = None,
        full_name: str | None = None,
        role: UserRole | None = None,
        is_active: bool | None = None,
    ) -> User | None:
        """Actualiza un usuario existente."""
        user = self.repository.get_by_id(user_id)
        if user is None:
            return None

        if email is not None:
            if self.repository.get_by_email(email) is not None:
                raise EmailAlreadyRegisteredError("El email ya está registrado")
            user.email = email

        if full_name is not None:
            user.full_name = full_name
        if role is not None:
            user.role = role
            company_id = get_company_id(self.db)
            if company_id is not None:
                self.companies.add_membership(user_id, company_id, role)
        if is_active is not None:
            user.is_active = is_active

        self.db.flush()
        self.db.refresh(user)
        return user
