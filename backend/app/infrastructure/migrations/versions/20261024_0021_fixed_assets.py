"""Activos fijos y depreciación mensual por línea recta.

Revision ID: 20261024_0021
Revises: 20261024_0020
Create Date: 2026-10-24

Crea las tablas ``fixed_assets`` y ``depreciation_entries``, extiende el ENUM
``accounting_entry_source_type`` con ``DEPRECIATION`` y siembra las cuentas
PUC 5160 (gasto por depreciación) y 1592 (depreciación acumulada).

La tabla ``depreciation_entries`` tiene una restricción única por
``(asset_id, date)``. La fecha se guarda como el último día del mes, por lo que
la restricción también impide dos cuotas para el mismo mes.

REQUIERE VALIDACIÓN: contador público colombiano para confirmar las cuentas
auxiliares 5160 y 1592 y la política de depreciación por línea recta.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "20261024_0021"
down_revision: str | None = "20261024_0020"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


fixed_asset_status_enum = postgresql.ENUM(
    "ACTIVE",
    "DISPOSED",
    name="fixed_asset_status",
    create_type=False,
)


# Se incluyen los padres para respetar la FK jerárquica del PUC. Todos los
# INSERT usan ON CONFLICT DO NOTHING para que la migración sea idempotente si
# el catálogo ya contiene alguna de estas cuentas.
FIXED_ASSET_PUC_SEED: tuple[dict[str, str | None], ...] = (
    {
        "code": "1",
        "name": "Activo",
        "account_type": "ACTIVO",
        "nature": "DEBITO",
        "parent_code": None,
    },
    {
        "code": "15",
        "name": "Propiedades, planta y equipo",
        "account_type": "ACTIVO",
        "nature": "DEBITO",
        "parent_code": "1",
    },
    {
        "code": "1592",
        "name": "Depreciación acumulada",
        "account_type": "ACTIVO",
        "nature": "CREDITO",
        "parent_code": "15",
    },
    {
        "code": "5",
        "name": "Gastos",
        "account_type": "GASTO",
        "nature": "DEBITO",
        "parent_code": None,
    },
    {
        "code": "51",
        "name": "Gastos operacionales",
        "account_type": "GASTO",
        "nature": "DEBITO",
        "parent_code": "5",
    },
    {
        "code": "5160",
        "name": "Gastos por depreciación",
        "account_type": "GASTO",
        "nature": "DEBITO",
        "parent_code": "51",
    },
)


def upgrade() -> None:
    # PostgreSQL permite agregar el valor dentro de la transacción de Alembic,
    # pero no usarlo en la misma transacción. Esta migración no inserta
    # asientos con el nuevo valor.
    op.execute("ALTER TYPE accounting_entry_source_type ADD VALUE IF NOT EXISTS 'DEPRECIATION'")

    bind = op.get_bind()
    fixed_asset_status_enum.create(bind, checkfirst=True)

    op.create_table(
        "fixed_assets",
        sa.Column(
            "id",
            sa.Uuid(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("purchase_date", sa.Date(), nullable=False),
        sa.Column("initial_cost", sa.Numeric(18, 2), nullable=False),
        sa.Column(
            "salvage_value",
            sa.Numeric(18, 2),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column("useful_life_months", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            fixed_asset_status_enum,
            server_default=sa.text("'ACTIVE'"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_fixed_assets"),
        sa.UniqueConstraint("code", name="uq_fixed_assets_code"),
        sa.CheckConstraint(
            "initial_cost > 0",
            name="ck_fixed_assets_initial_cost_positive",
        ),
        sa.CheckConstraint(
            "salvage_value >= 0",
            name="ck_fixed_assets_salvage_value_non_negative",
        ),
        sa.CheckConstraint(
            "salvage_value < initial_cost",
            name="ck_fixed_assets_salvage_value_less_than_cost",
        ),
        sa.CheckConstraint(
            "useful_life_months > 0",
            name="ck_fixed_assets_useful_life_positive",
        ),
    )
    op.create_index("ix_fixed_assets_purchase_date", "fixed_assets", ["purchase_date"])
    op.create_index("ix_fixed_assets_status", "fixed_assets", ["status"])

    op.create_table(
        "depreciation_entries",
        sa.Column(
            "id",
            sa.Uuid(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("asset_id", sa.Uuid(), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("accounting_entry_id", sa.Uuid(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_depreciation_entries"),
        sa.ForeignKeyConstraint(
            ["asset_id"],
            ["fixed_assets.id"],
            name="fk_depreciation_entries_asset_id_fixed_assets",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["accounting_entry_id"],
            ["accounting_entries.id"],
            name="fk_depreciation_entries_accounting_entry_id_accounting_entries",
            ondelete="SET NULL",
        ),
        sa.UniqueConstraint(
            "asset_id",
            "date",
            name="uq_depreciation_entries_asset_id_date",
        ),
        sa.CheckConstraint(
            "amount > 0",
            name="ck_depreciation_entries_amount_positive",
        ),
    )
    op.create_index(
        "ix_depreciation_entries_asset_id",
        "depreciation_entries",
        ["asset_id"],
    )
    op.create_index(
        "ix_depreciation_entries_date",
        "depreciation_entries",
        ["date"],
    )
    op.create_index(
        "ix_depreciation_entries_accounting_entry_id",
        "depreciation_entries",
        ["accounting_entry_id"],
    )

    connection = op.get_bind()
    insert_account = sa.text(
        """
        INSERT INTO accounting_accounts
            (code, name, account_type, nature, parent_code)
        VALUES
            (:code, :name,
             CAST(:account_type AS accounting_account_type),
             CAST(:nature AS accounting_account_nature),
             :parent_code)
        ON CONFLICT (code) DO NOTHING
        """
    )
    for account in FIXED_ASSET_PUC_SEED:
        connection.execute(insert_account, account)


def downgrade() -> None:
    op.drop_index(
        "ix_depreciation_entries_accounting_entry_id",
        table_name="depreciation_entries",
    )
    op.drop_index("ix_depreciation_entries_date", table_name="depreciation_entries")
    op.drop_index(
        "ix_depreciation_entries_asset_id",
        table_name="depreciation_entries",
    )
    op.drop_table("depreciation_entries")

    op.drop_index("ix_fixed_assets_status", table_name="fixed_assets")
    op.drop_index("ix_fixed_assets_purchase_date", table_name="fixed_assets")
    op.drop_table("fixed_assets")

    # Los asientos de depreciación quedarían huérfanos al eliminar las tablas.
    op.execute("DELETE FROM accounting_entries WHERE source_type = 'DEPRECIATION'")
    op.execute("DELETE FROM accounting_accounts WHERE code IN ('5160', '1592')")
    op.execute(
        """
        DELETE FROM accounting_accounts
        WHERE code = '15'
          AND NOT EXISTS (
              SELECT 1 FROM accounting_accounts WHERE parent_code = '15'
          )
        """
    )

    # PostgreSQL no permite eliminar un valor de un ENUM. Se reconstruye el
    # tipo conservando exactamente los valores existentes antes de esta
    # migración.
    op.execute("ALTER TYPE accounting_entry_source_type RENAME TO accounting_entry_source_type_old")
    op.execute(
        """
        CREATE TYPE accounting_entry_source_type AS ENUM (
            'INVOICE',
            'PAYMENT',
            'VOID',
            'PAYMENT_REVERSAL',
            'PAYROLL',
            'PURCHASE',
            'PURCHASE_PAYMENT',
            'CREDIT_NOTE',
            'EXPENSE',
            'EXPENSE_REVERSAL',
            'BANK_TRANSACTION'
        )
        """
    )
    op.execute(
        """
        ALTER TABLE accounting_entries
        ALTER COLUMN source_type TYPE accounting_entry_source_type
        USING source_type::text::accounting_entry_source_type
        """
    )
    op.execute("DROP TYPE accounting_entry_source_type_old")

    fixed_asset_status_enum.drop(op.get_bind(), checkfirst=True)
