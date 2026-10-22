"""Añade los campos de anulación a facturas.

Revision ID: 20261021_0002
Revises: 20261021_0001
Create Date: 2026-10-21

Ambas columnas son nullable: solo se llenan cuando una factura emitida pasa a
VOID. No se implementan notas crédito ni devolución de pagos en esta fase.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20261021_0002"
down_revision: str | None = "20261021_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "invoices",
        sa.Column("voided_reason", sa.String(length=500), nullable=True),
    )
    op.add_column(
        "invoices",
        sa.Column("voided_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("invoices", "voided_at")
    op.drop_column("invoices", "voided_reason")
