"""Utilidades transaccionales compartidas por los casos de uso."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy.orm import Session


@contextmanager
def operation_transaction(db: Session) -> Iterator[None]:
    """Agrupa una operación de negocio y sus efectos contables.

    En producción cada petición tiene una sesión nueva, así que se abre la
    transacción de nivel superior. En tests la sesión se comparte entre
    peticiones; si ya hay una transacción abierta se usa un savepoint para
    mantener el aislamiento y el rollback del test.
    """
    if db.in_transaction():
        with db.begin_nested():
            yield
    else:
        with db.begin():
            yield
