"""Bancos y tesorería: cuentas bancarias y movimientos con contabilización.

Revision ID: 20261024_0017
Revises: 20261024_0016
Create Date: 2026-10-24

Crea las tablas ``bank_accounts`` y ``bank_transactions``, agrega el valor
``BANK_TRANSACTION`` al ENUM de origen de asientos y siembra cuentas auxiliares
de bancos (11100501..11100503) para que dos cuentas bancarias puedan tener
códigos PUC distintos y una transferencia entre ellas tenga efecto contable.

REQUIERE VALIDACIÓN: contador público colombiano. Los códigos auxiliares de
bancos y la política de conciliación son una configuración inicial del MVP.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "20261024_0017"
down_revision: str | None = "20261024_0016"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


bank_account_type_enum = postgresql.ENUM(
    "CHECKING",
    "SAVINGS",
    name="bank_account_type",
    create_type=False,
)
bank_transaction_type_enum = postgresql.ENUM(
    "DEPOSIT",
    "WITHDRAWAL",
    "TRANSFER",
    name="bank_transaction_type",
    create_type=False,
)

# Cuentas auxiliares de bancos. La cuenta 111005 ya existe desde el catálogo
# inicial y sigue siendo la cuenta por defecto del módulo.
BANK_PUC_SEED: tuple[dict[str, str | None], ...] = (
    {
        "code": "11100501",
        "name": "Banco moneda nacional - cuenta 1",
        "account_type": "ACTIVO",
        "nature": "DEBITO",
        "parent_code": "111005",
    },
    {
        "code": "11100502",
        "name": "Banco moneda nacional - cuenta 2",
        "account_type": "ACTIVO",
        "nature": "DEBITO",
        "parent_code": "111005",
    },
    {
        "code": "11100503",
        "name": "Banco moneda nacional - cuenta 3",
        "account_type": "ACTIVO",
        "nature": "DEBITO",
        "parent_code": "111005",
    },
)


def upgrade() -> None:
    bind = op.get_bind()
    bank_account_type_enum.create(bind, checkfirst=True)
    bank_transaction_type_enum.create(bind, checkfirst=True)

    # Mismo patrón que las migraciones anteriores: el valor se agrega dentro
    # de la transacción y no se usa en ella (no se insertan asientos aquí).
    op.execute("ALTER TYPE accounting_entry_source_type ADD VALUE IF NOT EXISTS 'BANK_TRANSACTION'")

    op.create_table(
        "bank_accounts",
        sa.Column(
            "id",
            sa.Uuid(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("bank_name", sa.String(length=100), nullable=False),
        sa.Column("account_number", sa.String(length=50), nullable=False),
        sa.Column(
            "account_type",
            bank_account_type_enum,
            server_default=sa.text("'CHECKING'"),
            nullable=False,
        ),
        sa.Column(
            "currency",
            sa.String(length=3),
            server_default=sa.text("'COP'"),
            nullable=False,
        ),
        sa.Column("accounting_account_code", sa.String(length=20), nullable=False),
        sa.Column(
            "is_active",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
        sa.Column(
            "version",
            sa.Integer(),
            server_default=sa.text("1"),
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
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["accounting_account_code"],
            ["accounting_accounts.code"],
            name="fk_bank_accounts_accounting_account_code_accounting_accounts",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_bank_accounts"),
        sa.UniqueConstraint(
            "bank_name",
            "account_number",
            name="uq_bank_accounts_bank_name_account_number",
        ),
        sa.CheckConstraint(
            "currency = 'COP'",
            name="ck_bank_accounts_currency_cop",
        ),
    )
    op.create_index(
        "ix_bank_accounts_accounting_account_code",
        "bank_accounts",
        ["accounting_account_code"],
    )
    op.create_index("ix_bank_accounts_is_active", "bank_accounts", ["is_active"])

    op.create_table(
        "bank_transactions",
        sa.Column(
            "id",
            sa.Uuid(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("bank_account_id", sa.Uuid(), nullable=False),
        sa.Column("counterpart_account_id", sa.Uuid(), nullable=True),
        sa.Column(
            "transaction_type",
            bank_transaction_type_enum,
            nullable=False,
        ),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("description", sa.String(length=200), nullable=False),
        sa.Column("reference", sa.String(length=100), nullable=True),
        sa.Column("counterpart_account_code", sa.String(length=20), nullable=True),
        sa.Column(
            "is_reconciled",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column("reconciled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "version",
            sa.Integer(),
            server_default=sa.text("1"),
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
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["bank_account_id"],
            ["bank_accounts.id"],
            name="fk_bank_transactions_bank_account_id_bank_accounts",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["counterpart_account_id"],
            ["bank_accounts.id"],
            name="fk_bank_transactions_counterpart_account_id_bank_accounts",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["counterpart_account_code"],
            ["accounting_accounts.code"],
            name="fk_bank_transactions_counterpart_code_accounts",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_bank_transactions"),
        sa.CheckConstraint(
            "amount > 0",
            name="ck_bank_transactions_amount_positive",
        ),
        sa.CheckConstraint(
            """
            (
                transaction_type = 'TRANSFER'
                AND counterpart_account_id IS NOT NULL
                AND counterpart_account_code IS NULL
                AND counterpart_account_id <> bank_account_id
            )
            OR
            (
                transaction_type IN ('DEPOSIT', 'WITHDRAWAL')
                AND counterpart_account_id IS NULL
                AND counterpart_account_code IS NOT NULL
            )
            """,
            name="ck_bank_transactions_counterpart",
        ),
        sa.CheckConstraint(
            """
            (is_reconciled = false AND reconciled_at IS NULL)
            OR (is_reconciled = true AND reconciled_at IS NOT NULL)
            """,
            name="ck_bank_transactions_reconciliation_consistency",
        ),
    )
    op.create_index(
        "ix_bank_transactions_bank_account_id",
        "bank_transactions",
        ["bank_account_id"],
    )
    op.create_index(
        "ix_bank_transactions_counterpart_account_id",
        "bank_transactions",
        ["counterpart_account_id"],
    )
    op.create_index(
        "ix_bank_transactions_transaction_type",
        "bank_transactions",
        ["transaction_type"],
    )
    op.create_index("ix_bank_transactions_date", "bank_transactions", ["date"])
    op.create_index(
        "ix_bank_transactions_is_reconciled",
        "bank_transactions",
        ["is_reconciled"],
    )
    op.create_index(
        "ix_bank_transactions_counterpart_account_code",
        "bank_transactions",
        ["counterpart_account_code"],
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
    for account in BANK_PUC_SEED:
        connection.execute(insert_account, account)


def downgrade() -> None:
    op.drop_index(
        "ix_bank_transactions_counterpart_account_code",
        table_name="bank_transactions",
    )
    op.drop_index(
        "ix_bank_transactions_is_reconciled",
        table_name="bank_transactions",
    )
    op.drop_index("ix_bank_transactions_date", table_name="bank_transactions")
    op.drop_index(
        "ix_bank_transactions_transaction_type",
        table_name="bank_transactions",
    )
    op.drop_index(
        "ix_bank_transactions_counterpart_account_id",
        table_name="bank_transactions",
    )
    op.drop_index(
        "ix_bank_transactions_bank_account_id",
        table_name="bank_transactions",
    )
    op.drop_table("bank_transactions")

    op.drop_index("ix_bank_accounts_is_active", table_name="bank_accounts")
    op.drop_index(
        "ix_bank_accounts_accounting_account_code",
        table_name="bank_accounts",
    )
    op.drop_table("bank_accounts")

    # Los asientos de tesorería quedarían huérfanos. Se eliminan antes de
    # reconstruir el ENUM sin BANK_TRANSACTION.
    op.execute("DELETE FROM accounting_entries WHERE source_type = 'BANK_TRANSACTION'")
    op.execute("DELETE FROM accounting_accounts WHERE code IN ('11100501', '11100502', '11100503')")

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
            'EXPENSE_REVERSAL'
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

    bank_transaction_type_enum.drop(op.get_bind(), checkfirst=True)
    bank_account_type_enum.drop(op.get_bind(), checkfirst=True)
