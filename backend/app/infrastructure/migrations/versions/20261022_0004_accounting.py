"""Núcleo contable: catálogo PUC, asientos y movimientos.

Revision ID: 20261022_0004
Revises: 20261021_0003
Create Date: 2026-10-22

La migración crea las tres tablas del módulo, siembra un catálogo PUC mínimo y
añade un constraint trigger diferido que rechaza asientos desbalanceados al
commit. Los códigos y nombres sembrados REQUIEREN VALIDACIÓN por un contador
público colombiano antes de usarse en producción.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "20261022_0004"
down_revision: str | None = "20261021_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


account_type_enum = postgresql.ENUM(
    "ACTIVO",
    "PASIVO",
    "PATRIMONIO",
    "INGRESO",
    "GASTO",
    "COSTO",
    name="accounting_account_type",
    create_type=False,
)
account_nature_enum = postgresql.ENUM(
    "DEBITO",
    "CREDITO",
    name="accounting_account_nature",
    create_type=False,
)
source_type_enum = postgresql.ENUM(
    "INVOICE",
    "PAYMENT",
    "VOID",
    "PAYMENT_REVERSAL",
    name="accounting_entry_source_type",
    create_type=False,
)
entry_status_enum = postgresql.ENUM(
    "DRAFT",
    "POSTED",
    name="accounting_entry_status",
    create_type=False,
)


# Catálogo mínimo de demostración. En producción debe reemplazarse o ampliarse
# con el PUC aprobado por la empresa.
PUC_SEED: tuple[dict[str, str | None], ...] = (
    {
        "code": "1",
        "name": "Activo",
        "account_type": "ACTIVO",
        "nature": "DEBITO",
        "parent_code": None,
    },
    {
        "code": "13",
        "name": "Deudores",
        "account_type": "ACTIVO",
        "nature": "DEBITO",
        "parent_code": "1",
    },
    {
        "code": "1305",
        "name": "Clientes",
        "account_type": "ACTIVO",
        "nature": "DEBITO",
        "parent_code": "13",
    },
    {
        "code": "130505",
        "name": "Clientes nacionales",
        "account_type": "ACTIVO",
        "nature": "DEBITO",
        "parent_code": "1305",
    },
    {
        "code": "11",
        "name": "Disponible",
        "account_type": "ACTIVO",
        "nature": "DEBITO",
        "parent_code": "1",
    },
    {
        "code": "1105",
        "name": "Caja",
        "account_type": "ACTIVO",
        "nature": "DEBITO",
        "parent_code": "11",
    },
    {
        "code": "110505",
        "name": "Caja general",
        "account_type": "ACTIVO",
        "nature": "DEBITO",
        "parent_code": "1105",
    },
    {
        "code": "1110",
        "name": "Bancos",
        "account_type": "ACTIVO",
        "nature": "DEBITO",
        "parent_code": "11",
    },
    {
        "code": "111005",
        "name": "Bancos moneda nacional",
        "account_type": "ACTIVO",
        "nature": "DEBITO",
        "parent_code": "1110",
    },
    {
        "code": "2",
        "name": "Pasivo",
        "account_type": "PASIVO",
        "nature": "CREDITO",
        "parent_code": None,
    },
    {
        "code": "24",
        "name": "Impuestos, gravámenes y tasas",
        "account_type": "PASIVO",
        "nature": "CREDITO",
        "parent_code": "2",
    },
    {
        "code": "2408",
        "name": "Impuesto sobre las ventas por pagar",
        "account_type": "PASIVO",
        "nature": "CREDITO",
        "parent_code": "24",
    },
    {
        "code": "240801",
        "name": "IVA generado",
        "account_type": "PASIVO",
        "nature": "CREDITO",
        "parent_code": "2408",
    },
    {
        "code": "4",
        "name": "Ingresos",
        "account_type": "INGRESO",
        "nature": "CREDITO",
        "parent_code": None,
    },
    {
        "code": "41",
        "name": "Ingresos operacionales",
        "account_type": "INGRESO",
        "nature": "CREDITO",
        "parent_code": "4",
    },
    {
        "code": "4135",
        "name": "Comercio al por mayor y al por menor",
        "account_type": "INGRESO",
        "nature": "CREDITO",
        "parent_code": "41",
    },
    {
        "code": "413505",
        "name": "Comercio al por mayor y al por menor",
        "account_type": "INGRESO",
        "nature": "CREDITO",
        "parent_code": "4135",
    },
)


def upgrade() -> None:
    bind = op.get_bind()
    for enum_type in (
        account_type_enum,
        account_nature_enum,
        source_type_enum,
        entry_status_enum,
    ):
        enum_type.create(bind, checkfirst=True)

    op.create_table(
        "accounting_accounts",
        sa.Column("code", sa.String(length=20), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("account_type", account_type_enum, nullable=False),
        sa.Column("nature", account_nature_enum, nullable=False),
        sa.Column("parent_code", sa.String(length=20), nullable=True),
        sa.ForeignKeyConstraint(
            ["parent_code"],
            ["accounting_accounts.code"],
            name="fk_accounting_accounts_parent_code_accounting_accounts",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("code", name="pk_accounting_accounts"),
    )
    op.create_index(
        "ix_accounting_accounts_account_type",
        "accounting_accounts",
        ["account_type"],
        unique=False,
    )
    op.create_index(
        "ix_accounting_accounts_parent_code",
        "accounting_accounts",
        ["parent_code"],
        unique=False,
    )

    op.create_table(
        "accounting_entries",
        sa.Column(
            "id",
            sa.Uuid(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("entry_date", sa.Date(), nullable=False),
        sa.Column("description", sa.String(length=500), nullable=False),
        sa.Column("source_type", source_type_enum, nullable=False),
        sa.Column("source_id", sa.Uuid(), nullable=False),
        sa.Column(
            "status",
            entry_status_enum,
            server_default=sa.text("'POSTED'"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_accounting_entries"),
        sa.UniqueConstraint(
            "source_type",
            "source_id",
            name="uq_accounting_entries_source_type_source_id",
        ),
    )
    op.create_index(
        "ix_accounting_entries_entry_date",
        "accounting_entries",
        ["entry_date"],
        unique=False,
    )
    op.create_index(
        "ix_accounting_entries_source_type",
        "accounting_entries",
        ["source_type"],
        unique=False,
    )
    op.create_index(
        "ix_accounting_entries_source_id",
        "accounting_entries",
        ["source_id"],
        unique=False,
    )
    op.create_index(
        "ix_accounting_entries_status",
        "accounting_entries",
        ["status"],
        unique=False,
    )

    op.create_table(
        "accounting_entry_lines",
        sa.Column(
            "id",
            sa.Uuid(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("entry_id", sa.Uuid(), nullable=False),
        sa.Column("account_code", sa.String(length=20), nullable=False),
        sa.Column(
            "debit",
            sa.Numeric(precision=18, scale=2),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column(
            "credit",
            sa.Numeric(precision=18, scale=2),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "debit >= 0",
            name="ck_accounting_entry_lines_debit_non_negative",
        ),
        sa.CheckConstraint(
            "credit >= 0",
            name="ck_accounting_entry_lines_credit_non_negative",
        ),
        sa.CheckConstraint(
            "(debit > 0 AND credit = 0) OR (credit > 0 AND debit = 0)",
            name="ck_accounting_entry_lines_one_side_positive",
        ),
        sa.ForeignKeyConstraint(
            ["entry_id"],
            ["accounting_entries.id"],
            name="fk_accounting_entry_lines_entry_id_accounting_entries",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["account_code"],
            ["accounting_accounts.code"],
            name="fk_accounting_entry_lines_account_code_accounting_accounts",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_accounting_entry_lines"),
    )
    op.create_index(
        "ix_accounting_entry_lines_entry_id",
        "accounting_entry_lines",
        ["entry_id"],
        unique=False,
    )
    op.create_index(
        "ix_accounting_entry_lines_account_code",
        "accounting_entry_lines",
        ["account_code"],
        unique=False,
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
        """
    )
    for account in PUC_SEED:
        connection.execute(insert_account, account)

    # Red de seguridad a nivel de base de datos: el trigger es diferido para
    # permitir insertar todas las líneas y validar el asiento completo al commit.
    op.execute(
        """
        CREATE OR REPLACE FUNCTION accounting_entry_must_balance()
        RETURNS trigger AS $$
        DECLARE
            target_entry_id uuid;
            total_debit numeric(18, 2);
            total_credit numeric(18, 2);
        BEGIN
            target_entry_id := COALESCE(NEW.entry_id, OLD.entry_id);

            SELECT COALESCE(SUM(debit), 0), COALESCE(SUM(credit), 0)
              INTO total_debit, total_credit
              FROM accounting_entry_lines
             WHERE entry_id = target_entry_id;

            IF total_debit <> total_credit THEN
                RAISE EXCEPTION
                    'Asiento desbalanceado %: débitos %, créditos %',
                    target_entry_id, total_debit, total_credit
                    USING ERRCODE = 'check_violation';
            END IF;

            RETURN NULL;
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        """
        CREATE CONSTRAINT TRIGGER trg_accounting_entry_lines_balanced
        AFTER INSERT OR UPDATE OR DELETE ON accounting_entry_lines
        DEFERRABLE INITIALLY DEFERRED
        FOR EACH ROW EXECUTE FUNCTION accounting_entry_must_balance();
        """
    )

    op.execute(
        "COMMENT ON TABLE accounting_accounts IS "
        "'REQUIERE VALIDACIÓN: contador público colombiano. "
        "Catálogo PUC inicial del MVP.'"
    )
    op.execute(
        "COMMENT ON COLUMN accounting_accounts.code IS "
        "'Código PUC. REQUIERE VALIDACIÓN: contador público colombiano.'"
    )
    op.execute(
        "COMMENT ON COLUMN accounting_entries.source_id IS "
        "'UUID polimórfico: invoices.id o payments.id según source_type.'"
    )


def downgrade() -> None:
    op.execute(
        "DROP TRIGGER IF EXISTS trg_accounting_entry_lines_balanced ON accounting_entry_lines"
    )
    op.drop_table("accounting_entry_lines")
    op.drop_table("accounting_entries")
    op.drop_table("accounting_accounts")
    op.execute("DROP FUNCTION IF EXISTS accounting_entry_must_balance()")

    entry_status_enum.drop(op.get_bind(), checkfirst=True)
    source_type_enum.drop(op.get_bind(), checkfirst=True)
    account_nature_enum.drop(op.get_bind(), checkfirst=True)
    account_type_enum.drop(op.get_bind(), checkfirst=True)
