"""Módulo de Compras: contactos proveedor y facturas de compra.

Revision ID: 20261023_0008
Revises: 20261022_0007
Create Date: 2026-10-23

Añade la columna ``type`` (clasificación de contacto) a ``contacts`` y crea las
tablas ``purchase_invoices`` y ``purchase_lines`` para registrar facturas de
proveedores. También extiende el enum ``accounting_entry_source_type`` con el
valor ``PURCHASE`` para los asientos contables de compra.

REQUIERE VALIDACIÓN: contador/experto DIAN para los asientos contables de
compra (cuentas de inventario, IVA descontable y cuentas por pagar).
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "20261023_0008"
down_revision: str | None = "20261022_0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

contact_type_enum = postgresql.ENUM(
    "customer",
    "supplier",
    "both",
    name="contact_type",
    create_type=False,
)
purchase_status_enum = postgresql.ENUM(
    "DRAFT",
    "ISSUED",
    "VOID",
    name="purchase_invoice_status",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()

    # Nuevo ENUM de tipo de contacto.
    contact_type_enum.create(bind, checkfirst=True)

    # Añadir columna type a contacts.
    op.add_column(
        "contacts",
        sa.Column(
            "type",
            contact_type_enum,
            nullable=False,
            server_default=sa.text("'customer'"),
        ),
    )
    op.create_index(
        "ix_contacts_type",
        "contacts",
        ["type"],
        unique=False,
    )

    # Extender enum de origen de asientos con PURCHASE.
    op.execute("ALTER TYPE accounting_entry_source_type ADD VALUE IF NOT EXISTS 'PURCHASE'")

    # Nuevo ENUM de estado de factura de compra.
    purchase_status_enum.create(bind, checkfirst=True)

    op.create_table(
        "purchase_invoices",
        sa.Column(
            "id",
            sa.Uuid(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "supplier_id",
            sa.Uuid(),
            nullable=False,
        ),
        sa.Column("number", sa.String(length=50), nullable=True),
        sa.Column("issue_date", sa.Date(), nullable=True),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("status", purchase_status_enum, nullable=False),
        sa.Column(
            "subtotal",
            sa.Numeric(precision=18, scale=2),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column(
            "tax_total",
            sa.Numeric(precision=18, scale=2),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column(
            "total",
            sa.Numeric(precision=18, scale=2),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column(
            "balance",
            sa.Numeric(precision=18, scale=2),
            server_default=sa.text("0"),
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
        sa.ForeignKeyConstraint(
            ["supplier_id"],
            ["contacts.id"],
            name="fk_purchase_invoices_supplier_id_contacts",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_purchase_invoices"),
    )
    op.create_index(
        "ix_purchase_invoices_issue_date",
        "purchase_invoices",
        ["issue_date"],
        unique=False,
    )
    op.create_index(
        "ix_purchase_invoices_status",
        "purchase_invoices",
        ["status"],
        unique=False,
    )
    op.create_index(
        "ix_purchase_invoices_supplier_id",
        "purchase_invoices",
        ["supplier_id"],
        unique=False,
    )

    op.create_table(
        "purchase_lines",
        sa.Column(
            "id",
            sa.Uuid(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "purchase_invoice_id",
            sa.Uuid(),
            nullable=False,
        ),
        sa.Column(
            "item_id",
            sa.Uuid(),
            nullable=True,
        ),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column(
            "quantity",
            sa.Numeric(precision=18, scale=4),
            nullable=False,
        ),
        sa.Column(
            "unit_cost",
            sa.Numeric(precision=18, scale=2),
            nullable=False,
        ),
        sa.Column(
            "tax_rate",
            sa.Numeric(precision=7, scale=4),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column(
            "line_subtotal",
            sa.Numeric(precision=18, scale=2),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column(
            "line_tax",
            sa.Numeric(precision=18, scale=2),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column(
            "line_total",
            sa.Numeric(precision=18, scale=2),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "quantity > 0",
            name="ck_purchase_lines_quantity_positive",
        ),
        sa.CheckConstraint(
            "unit_cost >= 0",
            name="ck_purchase_lines_unit_cost_non_negative",
        ),
        sa.CheckConstraint(
            "tax_rate >= 0 AND tax_rate <= 100",
            name="ck_purchase_lines_tax_rate_range",
        ),
        sa.CheckConstraint(
            "line_subtotal >= 0",
            name="ck_purchase_lines_subtotal_non_negative",
        ),
        sa.CheckConstraint(
            "line_tax >= 0",
            name="ck_purchase_lines_tax_non_negative",
        ),
        sa.CheckConstraint(
            "line_total >= 0",
            name="ck_purchase_lines_total_non_negative",
        ),
        sa.ForeignKeyConstraint(
            ["item_id"],
            ["items.id"],
            name="fk_purchase_lines_item_id_items",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["purchase_invoice_id"],
            ["purchase_invoices.id"],
            name="fk_purchase_lines_purchase_invoice_id_purchase_invoices",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_purchase_lines"),
    )
    op.create_index(
        "ix_purchase_lines_item_id",
        "purchase_lines",
        ["item_id"],
        unique=False,
    )
    op.create_index(
        "ix_purchase_lines_purchase_invoice_id",
        "purchase_lines",
        ["purchase_invoice_id"],
        unique=False,
    )

    _seed_accounts()


def _seed_accounts() -> None:
    """Siembra cuentas PUC necesarias para los asientos de compra."""
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
    purchase_accounts = (
        {
            "code": "14",
            "name": "Inventario",
            "account_type": "ACTIVO",
            "nature": "DEBITO",
            "parent_code": "1",
        },
        {
            "code": "1435",
            "name": "Inventario de mercancías",
            "account_type": "ACTIVO",
            "nature": "DEBITO",
            "parent_code": "14",
        },
        {
            "code": "143505",
            "name": "Inventario de mercancías terminadas",
            "account_type": "ACTIVO",
            "nature": "DEBITO",
            "parent_code": "1435",
        },
        {
            "code": "22",
            "name": "Cuentas por pagar",
            "account_type": "PASIVO",
            "nature": "CREDITO",
            "parent_code": "2",
        },
        {
            "code": "2205",
            "name": "Compras y servicios por pagar",
            "account_type": "PASIVO",
            "nature": "CREDITO",
            "parent_code": "22",
        },
        {
            "code": "220505",
            "name": "Compras nacionales por pagar",
            "account_type": "PASIVO",
            "nature": "CREDITO",
            "parent_code": "2205",
        },
        {
            "code": "240802",
            "name": "IVA descontable",
            "account_type": "PASIVO",
            "nature": "CREDITO",
            "parent_code": "2408",
        },
    )
    for account in purchase_accounts:
        connection.execute(insert_account, account)


def downgrade() -> None:
    op.drop_index(
        "ix_purchase_lines_purchase_invoice_id",
        table_name="purchase_lines",
    )
    op.drop_index("ix_purchase_lines_item_id", table_name="purchase_lines")
    op.drop_table("purchase_lines")

    op.drop_index("ix_purchase_invoices_supplier_id", table_name="purchase_invoices")
    op.drop_index("ix_purchase_invoices_status", table_name="purchase_invoices")
    op.drop_index("ix_purchase_invoices_issue_date", table_name="purchase_invoices")
    op.drop_table("purchase_invoices")

    op.drop_index("ix_contacts_type", table_name="contacts")
    op.drop_column("contacts", "type")

    purchase_status_enum.drop(op.get_bind(), checkfirst=True)
    contact_type_enum.drop(op.get_bind(), checkfirst=True)
