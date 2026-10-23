"""Casos de uso de autenticación con sesiones opacas revocables."""

from __future__ import annotations

from datetime import UTC, datetime

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
from app.domain.auth_repository import AuthRepository
from app.domain.exceptions import (
    EmailAlreadyRegisteredError,
    InvalidCredentialsError,
    RegistrationClosedError,
)
from app.domain.models.auth import User
from app.infrastructure.transactions import operation_transaction


class AuthService:
    """Registro, login, logout y resolución de la sesión actual."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.repository = AuthRepository(db)

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

                return self.repository.add_user(
                    email=email,
                    hashed_password=hash_password(payload.password),
                    full_name=payload.full_name,
                )
        except IntegrityError as exc:
            # Carrera entre la verificación y el INSERT: gana el UNIQUE de la BD.
            raise EmailAlreadyRegisteredError("El email ya está registrado") from exc

    def login(self, payload: LoginRequest) -> tuple[User, str, datetime]:
        """Valida credenciales y crea una sesión de 24 horas."""
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

            token = generate_session_token()
            expires_at = now + SESSION_TTL
            self.repository.add_session(
                user_id=user.id,
                token_hash=hash_session_token(token),
                expires_at=expires_at,
            )

        return user, token, expires_at

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
