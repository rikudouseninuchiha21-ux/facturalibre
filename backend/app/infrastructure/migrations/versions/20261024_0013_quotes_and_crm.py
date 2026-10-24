"""CRM y cotizaciones: columna status en contacts, tablas quotes y quote_lines.

Revision ID: 20261024_0013
Revises: 20261023_0012
Create Date: 2026-10-24

Añade la columna ``status`` (LEAD / PROSPECT / CUSTOMER, default CUSTOMER) a la
tabla ``contacts`` y crea las tablas ``quotes`` y ``quote_lines`` para el módulo
de pre-ventas (CRM básico y cotizaciones).

REQUIERE VALIDACIÓN: contador/experto DIAN para la numeración de cotizaciones.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20261024_0013"
down_revision: str | None = "20261023_0012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Crear el tipo ENUM contact_status antes de usarlo en la columna.
    op.execute("CREATE TYPE contact_status AS ENUM ('LEAD', 'PROSPECT', 'CUSTOMER')")

    # Columna status en contacts (default CUSTOMER para no romper existentes).
    op.add_column(
        "contacts",
        sa.Column(
            "status",
            sa.Enum(
                "LEAD",
                "PROSPECT",
                "CUSTOMER",
                name="contact_status",
                native_enum=True,
                values_callable=lambda enum_cls: [m.value for m in enum_cls],
            ),
            nullable=False,
            server_default=sa.text("'CUSTOMER'"),
        ),
    )
    op.create_index("ix_contacts_status", "contacts", ["status"])

    # Tabla quotes.
    op.create_table(
        "quotes",
        sa.Column(
            "id",
            sa.Uuid(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("number", sa.String(length=50), nullable=True),
        sa.Column(
            "contact_id",
            sa.Uuid(),
            nullable=False,
        ),
        sa.Column("issue_date", sa.Date(), nullable=True, index=True),
        sa.Column("expiry_date", sa.Date(), nullable=True),
        sa.Column(
            "status",
            sa.Enum(
                "DRAFT",
                "SENT",
                "ACCEPTED",
                "REJECTED",
                "CONVERTED",
                name="quote_status",
                native_enum=True,
                values_callable=lambda enum_cls: [m.value for m in enum_cls],
            ),
            nullable=False,
            server_default=sa.text("'DRAFT'"),
        ),
        sa.Column(
            "converted_invoice_id",
            sa.Uuid(),
            nullable=True,
        ),
        sa.Column(
            "deleted_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "subtotal",
            sa.Numeric(18, 2),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "tax_total",
            sa.Numeric(18, 2),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "total",
            sa.Numeric(18, 2),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "currency",
            sa.String(length=3),
            nullable=False,
            server_default=sa.text("'COP'"),
        ),
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
        sa.ForeignKeyConstraint(
            ["contact_id"],
            ["contacts.id"],
            name="fk_quotes_contact_id_contacts",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["converted_invoice_id"],
            ["invoices.id"],
            name="fk_quotes_converted_invoice_id_invoices",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_quotes"),
        sa.UniqueConstraint("number", name="uq_quotes_number"),
        sa.CheckConstraint("subtotal >= 0", name="ck_quotes_subtotal_non_negative"),
        sa.CheckConstraint("tax_total >= 0", name="ck_quotes_tax_total_non_negative"),
        sa.CheckConstraint("total >= 0", name="ck_quotes_total_non_negative"),
        sa.CheckConstraint(
            "expiry_date IS NULL OR issue_date IS NULL OR expiry_date >= issue_date",
            name="ck_quotes_expiry_date_after_issue_date",
        ),
    )
    op.create_index("ix_quotes_contact_id", "quotes", ["contact_id"])
    op.create_index("ix_quotes_status", "quotes", ["status"])
    op.create_index(
        "ix_quotes_converted_invoice_id", "quotes", ["converted_invoice_id"]
    )

    # Tabla quote_lines.
    op.create_table(
        "quote_lines",
        sa.Column(
            "id",
            sa.Uuid(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "quote_id",
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
            sa.Numeric(18, 4),
            nullable=False,
        ),
        sa.Column(
            "unit_price",
            sa.Numeric(18, 2),
            nullable=False,
        ),
        sa.Column(
            "tax_rate",
            sa.Numeric(7, 4),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "line_subtotal",
            sa.Numeric(18, 2),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "line_tax",
            sa.Numeric(18, 2),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "line_total",
            sa.Numeric(18, 2),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.ForeignKeyConstraint(
            ["item_id"],
            ["items.id"],
            name="fk_quote_lines_item_id_items",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["quote_id"],
            ["quotes.id"],
            name="fk_quote_lines_quote_id_quotes",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_quote_lines"),
        sa.CheckConstraint("quantity > 0", name="ck_quote_lines_quantity_positive"),
        sa.CheckConstraint(
            "unit_price >= 0", name="ck_quote_lines_unit_price_non_negative"
        ),
        sa.CheckConstraint(
            "tax_rate >= 0 AND tax_rate <= 100",
            name="ck_quote_lines_tax_rate_range",
        ),
        sa.CheckConstraint(
            "line_subtotal >= 0", name="ck_quote_lines_subtotal_non_negative"
        ),
        sa.CheckConstraint("line_tax >= 0", name="ck_quote_lines_tax_non_negative"),
        sa.CheckConstraint("line_total >= 0", name="ck_quote_lines_total_non_negative"),
    )
    op.create_index("ix_quote_lines_quote_id", "quote_lines", ["quote_id"])
    op.create_index("ix_quote_lines_item_id", "quote_lines", ["item_id"])


def downgrade() -> None:
    op.drop_index("ix_quote_lines_item_id", table_name="quote_lines")
    op.drop_index("ix_quote_lines_quote_id", table_name="quote_lines")
    op.drop_table("quote_lines")

    op.drop_index("ix_quotes_converted_invoice_id", table_name="quotes")
    op.drop_index("ix_quotes_status", table_name="quotes")
    op.drop_index("ix_quotes_contact_id", table_name="quotes")
    op.drop_table("quotes")

    op.drop_index("ix_contacts_status", table_name="contacts")
    op.drop_column("contacts", "status")
    op.execute("DROP TYPE contact_status")
