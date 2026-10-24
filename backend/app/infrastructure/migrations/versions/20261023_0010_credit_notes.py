"""Notas Crédito para facturas de venta.

Revision ID: 20261023_0010
Revises: 20261023_0009
Create Date: 2026-10-23

Crea las tablas ``credit_notes`` y ``credit_note_lines`` para registrar notas
crédito asociadas a facturas de venta emitidas (devoluciones o errores fiscales),
y extiende el enum ``accounting_entry_source_type`` con el valor ``CREDIT_NOTE``
para los asientos contables de nota crédito.

REQUIERE VALIDACIÓN: contador/experto DIAN para los asientos contables de nota
crédito (débito a Ingresos, débito a IVA generado, crédito a Cuentas por Cobrar).
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20261023_0010"
down_revision: str | None = "20261023_0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Extender enum de origen de asientos con CREDIT_NOTE.
    op.execute("ALTER TYPE accounting_entry_source_type ADD VALUE IF NOT EXISTS 'CREDIT_NOTE'")

    op.create_table(
        "credit_notes",
        sa.Column(
            "id",
            sa.Uuid(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "invoice_id",
            sa.Uuid(),
            nullable=False,
        ),
        sa.Column("number", sa.String(length=50), nullable=True),
        sa.Column("issue_date", sa.Date(), nullable=True),
        sa.Column(
            "status",
            sa.String(length=20),
            nullable=False,
            server_default=sa.text("'draft'"),
        ),
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
            ["invoice_id"],
            ["invoices.id"],
            name="fk_credit_notes_invoice_id_invoices",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_credit_notes"),
    )
    op.create_index(
        "ix_credit_notes_invoice_id",
        "credit_notes",
        ["invoice_id"],
        unique=False,
    )
    op.create_index(
        "ix_credit_notes_issue_date",
        "credit_notes",
        ["issue_date"],
        unique=False,
    )

    op.create_table(
        "credit_note_lines",
        sa.Column(
            "id",
            sa.Uuid(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "credit_note_id",
            sa.Uuid(),
            nullable=False,
        ),
        sa.Column(
            "invoice_line_id",
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
            "unit_price",
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
            name="ck_credit_note_lines_quantity_positive",
        ),
        sa.CheckConstraint(
            "unit_price >= 0",
            name="ck_credit_note_lines_unit_price_non_negative",
        ),
        sa.CheckConstraint(
            "tax_rate >= 0 AND tax_rate <= 100",
            name="ck_credit_note_lines_tax_rate_range",
        ),
        sa.CheckConstraint(
            "line_subtotal >= 0",
            name="ck_credit_note_lines_subtotal_non_negative",
        ),
        sa.CheckConstraint(
            "line_tax >= 0",
            name="ck_credit_note_lines_tax_non_negative",
        ),
        sa.CheckConstraint(
            "line_total >= 0",
            name="ck_credit_note_lines_total_non_negative",
        ),
        sa.ForeignKeyConstraint(
            ["credit_note_id"],
            ["credit_notes.id"],
            name="fk_credit_note_lines_credit_note_id_credit_notes",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["invoice_line_id"],
            ["invoice_lines.id"],
            name="fk_credit_note_lines_invoice_line_id_invoice_lines",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_credit_note_lines"),
    )
    op.create_index(
        "ix_credit_note_lines_credit_note_id",
        "credit_note_lines",
        ["credit_note_id"],
        unique=False,
    )
    op.create_index(
        "ix_credit_note_lines_invoice_line_id",
        "credit_note_lines",
        ["invoice_line_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_credit_note_lines_invoice_line_id", table_name="credit_note_lines")
    op.drop_index("ix_credit_note_lines_credit_note_id", table_name="credit_note_lines")
    op.drop_table("credit_note_lines")

    op.drop_index("ix_credit_notes_issue_date", table_name="credit_notes")
    op.drop_index("ix_credit_notes_invoice_id", table_name="credit_notes")
    op.drop_table("credit_notes")
