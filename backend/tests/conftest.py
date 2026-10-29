"""Fixtures de integración para los endpoints CRUD."""

from __future__ import annotations

import os
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine, select, text
from sqlalchemy.orm import Session

from app.application.auth.security import SESSION_COOKIE_NAME, hash_session_token
from app.domain.models.auth import AuthSession, User
from app.domain.models.company import Company

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")

# La app crea su engine al importarse. En tests lo apuntamos a la base de test
# antes de importar app.main, sin recurrir al .env de desarrollo.
if TEST_DATABASE_URL:
    os.environ["DATABASE_URL"] = TEST_DATABASE_URL
    # La suite corre en un solo proceso: desactiva el rate limit de login
    # salvo en los tests que lo prueban (lo activan con monkeypatch).
    os.environ.setdefault("ENVIRONMENT", "test")


@pytest.fixture(scope="session")
def test_engine() -> Iterator[Engine]:
    """Engine de PostgreSQL real, separado de la base de desarrollo."""
    if not TEST_DATABASE_URL:
        pytest.skip(
            "Define TEST_DATABASE_URL con una base PostgreSQL de test migrada "
            "para ejecutar los tests CRUD."
        )

    engine = create_engine(TEST_DATABASE_URL, pool_pre_ping=True)
    with engine.connect() as connection:
        schema_exists = connection.scalar(text("SELECT to_regclass('public.contacts')"))
    if schema_exists is None:
        engine.dispose()
        pytest.skip("La base de test no tiene el esquema; ejecuta alembic upgrade head")

    try:
        yield engine
    finally:
        engine.dispose()


@pytest.fixture
def db_session(test_engine: Engine) -> Iterator[Session]:
    """Sesión aislada: cada test termina con rollback de su transacción externa."""
    connection = test_engine.connect()
    transaction = connection.begin()
    session = Session(
        bind=connection,
        join_transaction_mode="create_savepoint",
        expire_on_commit=False,
    )
    company_id = session.scalar(
        select(Company.id).order_by(Company.created_at, Company.id).limit(1)
    )
    if company_id is None:
        raise RuntimeError("La base de test no tiene una empresa inicial")
    session.info["company_id"] = company_id
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


def _test_client(db_session: Session) -> tuple[TestClient, FastAPI]:
    """Construye un TestClient aislado con get_db apuntando al test."""
    from app.infrastructure.database import get_db
    from app.main import app

    def override_get_db() -> Iterator[Session]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app, base_url="https://testserver"), app


@pytest.fixture
def anonymous_client(db_session: Session) -> Iterator[TestClient]:
    """Cliente sin cookie de sesión para probar login y registro."""
    test_client, app = _test_client(db_session)
    try:
        with test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()


@pytest.fixture
def client(anonymous_client: TestClient, db_session: Session) -> Iterator[TestClient]:
    """Cliente autenticado para los tests de módulos protegidos.

    La sesión se inserta directamente para no ejecutar bcrypt en cada test.
    """
    user = User(
        email=f"test-{uuid4()}@example.com",
        hashed_password="not-used-by-protected-endpoint-tests",
        full_name="Usuario de Prueba",
    )
    db_session.add(user)
    db_session.flush()

    token = str(uuid4())
    db_session.add(
        AuthSession(
            user_id=user.id,
            token=hash_session_token(token),
            expires_at=datetime.now(UTC) + timedelta(hours=1),
        )
    )
    db_session.flush()

    anonymous_client.cookies.set(
        SESSION_COOKIE_NAME,
        token,
        path="/",
    )
    yield anonymous_client
