"""Primitivas de seguridad para autenticación con sesiones opacas."""

from __future__ import annotations

import hashlib
import uuid
from datetime import timedelta

from passlib.context import CryptContext

from app.core.config import get_settings

SESSION_COOKIE_NAME = "facturalibre_session"


def session_cookie_secure() -> bool:
    """Flag ``Secure`` de la cookie de sesión según el entorno.

    ``True`` solo en producción: con HTTPS el navegador la rechaza si no
    viaja por un canal seguro. En ``http://localhost`` (desarrollo y tests)
    debe ser ``False`` o el navegador bloquea la cookie y no hay sesión.
    """
    return get_settings().environment.strip().lower() in {"production", "prod"}


SESSION_TTL = timedelta(hours=24)
SESSION_TTL_SECONDS = int(SESSION_TTL.total_seconds())

# Coste 12: mínimo recomendado (OWASP) para bcrypt.
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=12,
)

# Hash de un valor aleatorio conocido. Se usa para ejecutar bcrypt aunque el
# email no exista y reducir diferencias de tiempo entre ambos casos.
DUMMY_PASSWORD_HASH = pwd_context.hash("dummy-password-for-timing-only")


def hash_password(password: str) -> str:
    """Genera un hash bcrypt de la contraseña."""
    return pwd_context.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    """Verifica una contraseña contra su hash bcrypt."""
    return pwd_context.verify(password, hashed_password)


def generate_session_token() -> str:
    """Genera un token opaco con UUID v4 (122 bits de aleatoriedad)."""
    return str(uuid.uuid4())


def hash_session_token(token: str) -> str:
    """Devuelve el hash SHA-256 que se almacena en la tabla de sesiones."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
