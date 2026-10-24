"""Acceso a datos de usuarios y sesiones opacas."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, cast
from uuid import UUID

from sqlalchemy import delete, func, select, text
from sqlalchemy.engine import CursorResult
from sqlalchemy.orm import Session

from app.domain.models.auth import AuthSession, User, UserRole

# Clave fija para serializar el bootstrap del primer usuario.
_REGISTRATION_LOCK_KEY = 0x464143545552414C  # "FACTURAL"


class AuthRepository:
    """Operaciones de identidad sobre SQLAlchemy."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def lock_registration(self) -> None:
        """Serializa registros concurrentes durante la transacción actual."""
        self.db.execute(
            text("SELECT pg_advisory_xact_lock(:lock_key)"),
            {"lock_key": _REGISTRATION_LOCK_KEY},
        )

    def count_users(self) -> int:
        """Cuenta los usuarios existentes."""
        count = self.db.scalar(select(func.count()).select_from(User))
        return int(count or 0)

    def get_by_email(self, email: str) -> User | None:
        """Busca un usuario por email ya normalizado."""
        return self.db.scalar(select(User).where(User.email == email))

    def get_by_id(self, user_id: UUID) -> User | None:
        """Busca un usuario por su ID."""
        return self.db.scalar(select(User).where(User.id == user_id))

    def add_user(
        self,
        *,
        email: str,
        hashed_password: str,
        full_name: str,
        role: UserRole = UserRole.ADMIN,
    ) -> User:
        """Agrega un usuario a la transacción actual."""
        user = User(
            email=email,
            hashed_password=hashed_password,
            full_name=full_name,
            role=role,
        )
        self.db.add(user)
        self.db.flush()
        return user

    def add_session(
        self,
        *,
        user_id: UUID,
        token_hash: str,
        expires_at: datetime,
    ) -> AuthSession:
        """Agrega una sesión a la transacción actual."""
        session = AuthSession(
            user_id=user_id,
            token=token_hash,
            expires_at=expires_at,
        )
        self.db.add(session)
        self.db.flush()
        return session

    def get_user_by_session(self, token_hash: str) -> User | None:
        """Devuelve el usuario activo asociado a una sesión vigente."""
        statement = (
            select(User)
            .join(AuthSession)
            .where(
                AuthSession.token == token_hash,
                AuthSession.expires_at > datetime.now(UTC),
                User.is_active.is_(True),
            )
        )
        return self.db.scalar(statement)

    def delete_session(self, token_hash: str) -> bool:
        """Elimina una sesión por el hash de su token."""
        result = cast(
            CursorResult[Any],
            self.db.execute(delete(AuthSession).where(AuthSession.token == token_hash)),
        )
        return bool(result.rowcount)

    def list_users(self) -> list[User]:
        """Lista todos los usuarios registrados."""
        statement = select(User).order_by(User.created_at.desc())
        return list(self.db.scalars(statement))

    def update_user(
        self,
        user_id: UUID,
        *,
        email: str | None = None,
        full_name: str | None = None,
        role: UserRole | None = None,
        is_active: bool | None = None,
    ) -> User | None:
        """Actualiza campos de un usuario."""
        user = self.db.scalar(select(User).where(User.id == user_id))
        if user is None:
            return None

        if email is not None:
            user.email = email
        if full_name is not None:
            user.full_name = full_name
        if role is not None:
            user.role = role
        if is_active is not None:
            user.is_active = is_active

        self.db.flush()
        self.db.refresh(user)
        return user
