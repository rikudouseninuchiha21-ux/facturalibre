"""Centros de costo y presupuestos mensuales por cuenta PUC.

Revision ID: 20261024_0023
Revises: 20261024_0022
Create Date: 2026-10-25

Crea las tablas ``cost_centers``, ``budgets`` y ``budget_lines`` y agrega la
dimensión opcional ``cost_center_id`` a ``accounting_entry_lines`` y a los
documentos que la propagan (``purchase_invoices``, ``expenses`` y
``payroll_periods``).

La columna es NULL-able en todos los casos: los asientos históricos y los
documentos sin etiqueta no se atribuyen a ningún centro de costo.

El FK de ``budget_lines`` apunta a ``accounting_accounts.code`` (VARCHAR),
que es la clave primaria real del catálogo PUC del proyecto, no un UUID.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "20261024_0023"
down_revision: str | None = "20261024_0022"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# create_type=False evita que el CREATE TABLE de budgets intente crear el
# ENUM una segunda vez; el tipo se crea explícitamente en upgrade() (mismo
# patrón que la migración de tesorería 20261024_0017).
budget_status_enum = postgresql.ENUM(
    "DRAFT",
    "APPROVED",
    "CLOSED",
    name="budget_status",
    create_type=False,
)

# Documentos que propagan su centro de costo a las líneas del asiento.
TAGGED_TABLES: tuple[str, ...] = (
    "accounting_entry_lines",
    "purchase_invoices",
    "expenses",
    "payroll_periods",
)


def _add_cost_center_column(table: str) -> None:
    """Agrega cost_center_id NULLable con FK e índice a una tabla existente."""
    op.add_column(table, sa.Column("cost_center_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        f"fk_{table}_cost_center_id",
        table,
        "cost_centers",
        ["cost_center_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_index(f"ix_{table}_cost_center_id", table, ["cost_center_id"])


def _drop_cost_center_column(table: str) -> None:
    """Revierte la columna cost_center_id de una tabla existente."""
    op.drop_index(f"ix_{table}_cost_center_id", table_name=table)
    op.drop_constraint(f"fk_{table}_cost_center_id", table, type_="foreignkey")
    op.drop_column(table, "cost_center_id")


def upgrade() -> None:
    bind = op.get_bind()
    budget_status_enum.create(bind, checkfirst=True)

    op.create_table(
        "cost_centers",
        sa.Column(
            "id",
            sa.Uuid(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("code", sa.String(length=20), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "is_active",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_cost_centers"),
        sa.UniqueConstraint("code", name="uq_cost_centers_code"),
    )
    op.create_index("ix_cost_centers_is_active", "cost_centers", ["is_active"])

    op.create_table(
        "budgets",
        sa.Column(
            "id",
            sa.Uuid(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("cost_center_id", sa.Uuid(), nullable=False),
        sa.Column("period_year", sa.Integer(), nullable=False),
        sa.Column("period_month", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=150), nullable=True),
        sa.Column(
            "status",
            budget_status_enum,
            server_default=sa.text("'DRAFT'"),
            nullable=False,
        ),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_budgets"),
        sa.ForeignKeyConstraint(
            ["cost_center_id"],
            ["cost_centers.id"],
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint(
            "cost_center_id",
            "period_year",
            "period_month",
            name="uq_budgets_cost_center_period",
        ),
        sa.CheckConstraint(
            "period_month BETWEEN 1 AND 12",
            name="ck_budgets_month_range",
        ),
        sa.CheckConstraint(
            "period_year BETWEEN 2000 AND 2100",
            name="ck_budgets_year_range",
        ),
    )
    op.create_index("ix_budgets_cost_center_id", "budgets", ["cost_center_id"])
    op.create_index("ix_budgets_status", "budgets", ["status"])
    op.create_index(
        "ix_budgets_period",
        "budgets",
        ["period_year", "period_month"],
    )

    op.create_table(
        "budget_lines",
        sa.Column(
            "id",
            sa.Uuid(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("budget_id", sa.Uuid(), nullable=False),
        sa.Column("account_code", sa.String(length=20), nullable=False),
        sa.Column("amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_budget_lines"),
        sa.ForeignKeyConstraint(
            ["budget_id"],
            ["budgets.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["account_code"],
            ["accounting_accounts.code"],
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint(
            "amount >= 0",
            name="ck_budget_lines_amount_non_negative",
        ),
        sa.UniqueConstraint(
            "budget_id",
            "account_code",
            name="uq_budget_lines_budget_account",
        ),
    )
    op.create_index("ix_budget_lines_budget_id", "budget_lines", ["budget_id"])

    # Dimensión contable opcional, hacia atrás compatible (NULL por defecto).
    for table in TAGGED_TABLES:
        _add_cost_center_column(table)


def downgrade() -> None:
    for table in reversed(TAGGED_TABLES):
        _drop_cost_center_column(table)

    op.drop_index("ix_budget_lines_budget_id", table_name="budget_lines")
    op.drop_table("budget_lines")
    op.drop_index("ix_budgets_period", table_name="budgets")
    op.drop_index("ix_budgets_status", table_name="budgets")
    op.drop_index("ix_budgets_cost_center_id", table_name="budgets")
    op.drop_table("budgets")
    op.drop_index("ix_cost_centers_is_active", table_name="cost_centers")
    op.drop_table("cost_centers")

    budget_status_enum.drop(bind=op.get_bind(), checkfirst=True)
