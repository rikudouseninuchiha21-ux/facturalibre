"""Periodos contables mensuales y bloqueo de asientos en meses cerrados.

Revision ID: 20261024_0020
Revises: 20261024_0019
Create Date: 2026-10-24

La tabla ``fiscal_periods`` guarda únicamente los meses que se han cerrado.
La ausencia de fila equivale a un periodo abierto. La restricción única
``(month, year)`` garantiza un solo estado por mes calendario y los CHECK
limitan el mes al rango 1-12 y el año a valores razonables.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "20261024_0020"
down_revision: str | None = "20261024_0019"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


fiscal_period_status_enum = postgresql.ENUM(
    "OPEN",
    "CLOSED",
    name="fiscal_period_status",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    fiscal_period_status_enum.create(bind, checkfirst=True)

    op.create_table(
        "fiscal_periods",
        sa.Column(
            "id",
            sa.Uuid(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("month", sa.Integer(), nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            fiscal_period_status_enum,
            server_default=sa.text("'OPEN'"),
            nullable=False,
        ),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "month >= 1 AND month <= 12",
            name="ck_fiscal_periods_month_range",
        ),
        sa.CheckConstraint(
            "year >= 2000",
            name="ck_fiscal_periods_year_min",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_fiscal_periods"),
        sa.UniqueConstraint(
            "month",
            "year",
            name="uq_fiscal_periods_month_year",
        ),
    )
    op.create_index(
        "ix_fiscal_periods_year_month",
        "fiscal_periods",
        ["year", "month"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_fiscal_periods_year_month", table_name="fiscal_periods")
    op.drop_table("fiscal_periods")
    fiscal_period_status_enum.drop(op.get_bind(), checkfirst=True)
