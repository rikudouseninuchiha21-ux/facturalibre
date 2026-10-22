"""Pruebas de esquema contra un PostgreSQL real de test.

Requieren que las migraciones estén aplicadas en la base apuntada por
``TEST_DATABASE_URL``. No usan SQLite: el esquema depende de tipos nativos de
PostgreSQL (UUID, JSONB y ENUM).
"""

from __future__ import annotations

import os
from collections.abc import Iterator

import pytest
from sqlalchemy import Engine, Float, Numeric, create_engine, inspect

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")

pytestmark = pytest.mark.skipif(
    not TEST_DATABASE_URL,
    reason=(
        "Define TEST_DATABASE_URL apuntando a una base PostgreSQL de test "
        "con 'alembic upgrade head' aplicado."
    ),
)

EXPECTED_TABLES = {
    "accounting_accounts",
    "accounting_entries",
    "accounting_entry_lines",
    "contacts",
    "idempotency_keys",
    "invoice_lines",
    "invoices",
    "items",
    "number_sequences",
    "payments",
    "taxes",
}

MONETARY_COLUMNS: dict[str, tuple[str, ...]] = {
    "accounting_entry_lines": ("debit", "credit"),
    "items": ("unit_price",),
    "invoices": ("subtotal", "tax_total", "total", "balance"),
    "invoice_lines": (
        "unit_price",
        "tax_rate",
        "line_subtotal",
        "line_tax",
        "line_total",
    ),
    "payments": ("amount",),
    "taxes": ("rate",),
}


@pytest.fixture(scope="session")
def engine() -> Iterator[Engine]:
    """Engine de solo lectura contra la base de test ya migrada."""
    assert TEST_DATABASE_URL is not None
    test_engine = create_engine(TEST_DATABASE_URL, pool_pre_ping=True)
    try:
        yield test_engine
    finally:
        test_engine.dispose()


def test_all_tables_exist(engine: Engine) -> None:
    """El inspector ve las ocho tablas de negocio creadas por la migración."""
    table_names = set(inspect(engine).get_table_names())
    assert EXPECTED_TABLES <= table_names

    # Alembic deja su propia tabla de control; no forma parte del dominio.
    assert "alembic_version" in table_names


def test_invoice_has_two_separate_status_columns(engine: Engine) -> None:
    """Ciclo de vida y estado de pago son columnas distintas, no una sola."""
    columns = {column["name"] for column in inspect(engine).get_columns("invoices")}

    assert "lifecycle_status" in columns
    assert "payment_status" in columns
    assert "status" not in columns
    assert "lifecycle_status" != "payment_status"


def test_monetary_columns_are_numeric_not_float(engine: Engine) -> None:
    """Todo monto o tasa se guarda con NUMERIC/DECIMAL, nunca con FLOAT."""
    inspector = inspect(engine)

    for table_name, column_names in MONETARY_COLUMNS.items():
        columns = {column["name"]: column for column in inspector.get_columns(table_name)}
        for column_name in column_names:
            column_type = columns[column_name]["type"]
            assert isinstance(column_type, Numeric), (
                f"{table_name}.{column_name} debe ser NUMERIC, pero es {column_type!r}"
            )
            assert not isinstance(column_type, Float), (
                f"{table_name}.{column_name} no puede ser FLOAT"
            )


def test_version_columns_and_idempotency_unique_key(engine: Engine) -> None:
    """Los agregados editables tienen version y la clave idempotente es única."""
    inspector = inspect(engine)

    for table_name in ("contacts", "items", "taxes", "invoices", "number_sequences"):
        columns = {column["name"] for column in inspector.get_columns(table_name)}
        assert "version" in columns, f"{table_name} debe tener columna version"

    unique_columns = {
        tuple(constraint["column_names"])
        for constraint in inspector.get_unique_constraints("idempotency_keys")
    }
    assert ("key",) in unique_columns
