"""Gastos operativos: tabla expenses, cuentas PUC y valores de origen contable.

Revision ID: 20261024_0016
Revises: 20261024_0015
Create Date: 2026-10-24

Crea la tabla ``expenses`` para registrar gastos operativos (arriendo,
servicios, papelería, etc.), siembra la cuenta PUC 5199 (gastos diversos) y
agrega los valores ``EXPENSE`` y ``EXPENSE_REVERSAL`` al ENUM
``accounting_entry_source_type``.

El valor ``EXPENSE_REVERSAL`` permite revertir el asiento cuando se elimina
lógicamente un gasto, manteniendo el libro contable consistente.

REQUIERE VALIDACIÓN: contador/experto DIAN para la cuenta de gastos diversos
(5199) y las cuentas de caja/bancos (110505/111005).
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20261024_0016"
down_revision: str | None = "20261024_0015"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# La cuenta 5199 es la cuenta de gastos diversos usada por el asiento
# automático. Los padres 5 y 51 ya existen desde la migración de nómina; se
# incluyen con ON CONFLICT para que la migración sea idempotente si el catálogo
# se sembró parcialmente.
EXPENSE_PUC_SEED: tuple[dict[str, str | None], ...] = (
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
        "code": "5199",
        "name": "Gastos diversos",
        "account_type": "GASTO",
        "nature": "DEBITO",
        "parent_code": "51",
    },
)


def upgrade() -> None:
    # PostgreSQL 12+ permite agregar valores a un ENUM dentro de la
    # transacción de Alembic, pero no usarlos en la misma transacción. Esta
    # migración no inserta asientos con esos valores.
    op.execute("ALTER TYPE accounting_entry_source_type ADD VALUE IF NOT EXISTS 'EXPENSE'")
    op.execute("ALTER TYPE accounting_entry_source_type ADD VALUE IF NOT EXISTS 'EXPENSE_REVERSAL'")

    op.create_table(
        "expenses",
        sa.Column(
            "id",
            sa.Uuid(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("concept", sa.String(length=200), nullable=False),
        sa.Column(
            "amount",
            sa.Numeric(18, 2),
            nullable=False,
        ),
        sa.Column("payment_method", sa.String(length=50), nullable=False),
        sa.Column("reference", sa.String(length=200), nullable=True),
        sa.Column(
            "version",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("1"),
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
        sa.Column(
            "deleted_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_expenses"),
        sa.CheckConstraint("amount > 0", name="ck_expenses_amount_positive"),
    )
    op.create_index("ix_expenses_date", "expenses", ["date"])

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
    for account in EXPENSE_PUC_SEED:
        connection.execute(insert_account, account)


def downgrade() -> None:
    op.drop_index("ix_expenses_date", table_name="expenses")
    op.drop_table("expenses")

    # Los asientos de gastos quedarían huérfanos al eliminar la tabla. Se
    # eliminan antes de reconstruir el ENUM sin los valores de gastos.
    op.execute(
        "DELETE FROM accounting_entries WHERE source_type IN ('EXPENSE', 'EXPENSE_REVERSAL')"
    )
    op.execute("DELETE FROM accounting_accounts WHERE code = '5199'")

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
            'CREDIT_NOTE'
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
