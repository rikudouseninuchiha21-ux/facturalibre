"""Añade soft delete a facturas.

Revision ID: 20261021_0003
Revises: 20261021_0002
Create Date: 2026-10-21

Las facturas borradas conservan la fila y se excluyen de las consultas con
deleted_at IS NULL. El índice parcial acelera esas consultas habituales.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20261021_0003"
down_revision: str | None = "20261021_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "invoices",
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_invoices_not_deleted",
        "invoices",
        ["id"],
        unique=False,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )


def downgrade() -> None:
    op.drop_index("ix_invoices_not_deleted", table_name="invoices")
    op.drop_column("invoices", "deleted_at")
