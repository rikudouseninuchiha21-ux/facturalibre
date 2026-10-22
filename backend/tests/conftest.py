"""Fixtures de integración para los endpoints CRUD."""

from __future__ import annotations

import os
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.orm import Session

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")

# La app crea su engine al importarse. En tests lo apuntamos a la base de test
# antes de importar app.main, sin recurrir al .env de desarrollo.
if TEST_DATABASE_URL:
    os.environ["DATABASE_URL"] = TEST_DATABASE_URL


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
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture
def client(db_session: Session) -> Iterator[TestClient]:
    """TestClient con get_db apuntando a la sesión transaccional del test."""
    from app.infrastructure.database import get_db
    from app.main import app

    def override_get_db() -> Iterator[Session]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()
