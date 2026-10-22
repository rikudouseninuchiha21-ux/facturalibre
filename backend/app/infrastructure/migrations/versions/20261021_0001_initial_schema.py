"""Modelo inicial: contactos, ítems, impuestos, facturas, pagos, numeración e idempotencia.

Revision ID: 20261021_0001
Revises:
Create Date: 2026-10-21

Esta migración solo crea el esquema. No implementa emisión electrónica DIAN,
CUFE/CUDE ni firma electrónica: esos campos se incorporarán cuando exista una
decisión y validación explícitas.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "20261021_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


lifecycle_status_enum = postgresql.ENUM(
    "draft",
    "issued",
    "void",
    name="invoice_lifecycle_status",
    create_type=False,
)
payment_status_enum = postgresql.ENUM(
    "unpaid",
    "partially_paid",
    "paid",
    "overpaid",
    name="invoice_payment_status",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    lifecycle_status_enum.create(bind, checkfirst=True)
    payment_status_enum.create(bind, checkfirst=True)

    op.create_table(
        "taxes",
        sa.Column(
            "id",
            sa.Uuid(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=100), nullable=False),
        # -- REQUIERE VALIDACIÓN: contador/experto DIAN (tarifa y catálogo).
        # NUMERIC(7,4) admite 19.0000 %; NUMERIC(5,4) solo llegaría a 9.9999 %.
        sa.Column("rate", sa.Numeric(precision=7, scale=4), nullable=False),
        sa.Column("version", sa.Integer(), server_default=sa.text("1"), nullable=False),
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
        sa.CheckConstraint("rate >= 0 AND rate <= 100", name="ck_taxes_rate_range"),
        sa.PrimaryKeyConstraint("id", name="pk_taxes"),
    )

    op.create_table(
        "contacts",
        sa.Column(
            "id",
            sa.Uuid(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=True),
        # -- REQUIERE VALIDACIÓN: contador/experto DIAN (identificación fiscal).
        sa.Column("tax_id", sa.String(length=30), nullable=True),
        sa.Column("version", sa.Integer(), server_default=sa.text("1"), nullable=False),
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
        sa.PrimaryKeyConstraint("id", name="pk_contacts"),
    )

    op.create_table(
        "items",
        sa.Column(
            "id",
            sa.Uuid(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "unit_price",
            sa.Numeric(precision=18, scale=2),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column("tax_id", sa.Uuid(), nullable=True),
        sa.Column("version", sa.Integer(), server_default=sa.text("1"), nullable=False),
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
        sa.ForeignKeyConstraint(["tax_id"], ["taxes.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id", name="pk_items"),
    )
    op.create_index("ix_items_tax_id", "items", ["tax_id"], unique=False)

    op.create_table(
        "invoices",
        sa.Column(
            "id",
            sa.Uuid(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        # -- REQUIERE VALIDACIÓN: contador/experto DIAN (numeración autorizada).
        sa.Column("number", sa.String(length=50), nullable=True),
        sa.Column("contact_id", sa.Uuid(), nullable=False),
        # -- REQUIERE VALIDACIÓN: contador/experto DIAN (fecha de emisión).
        sa.Column("issue_date", sa.Date(), nullable=True),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column(
            "lifecycle_status",
            lifecycle_status_enum,
            server_default=sa.text("'draft'"),
            nullable=False,
        ),
        sa.Column(
            "payment_status",
            payment_status_enum,
            server_default=sa.text("'unpaid'"),
            nullable=False,
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
            "balance",
            sa.Numeric(precision=18, scale=2),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column(
            "currency",
            sa.CHAR(length=3),
            server_default=sa.text("'COP'"),
            nullable=False,
        ),
        sa.Column("version", sa.Integer(), server_default=sa.text("1"), nullable=False),
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
        sa.CheckConstraint("subtotal >= 0", name="ck_invoices_subtotal_non_negative"),
        sa.CheckConstraint("tax_total >= 0", name="ck_invoices_tax_total_non_negative"),
        sa.CheckConstraint("total >= 0", name="ck_invoices_total_non_negative"),
        sa.CheckConstraint("balance >= 0", name="ck_invoices_balance_non_negative"),
        sa.CheckConstraint("currency = 'COP'", name="ck_invoices_currency_cop"),
        sa.CheckConstraint(
            "due_date IS NULL OR issue_date IS NULL OR due_date >= issue_date",
            name="ck_invoices_due_date_after_issue_date",
        ),
        sa.ForeignKeyConstraint(["contact_id"], ["contacts.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id", name="pk_invoices"),
        sa.UniqueConstraint("number", name="uq_invoices_number"),
    )
    op.create_index("ix_invoices_contact_id", "invoices", ["contact_id"], unique=False)
    op.create_index("ix_invoices_issue_date", "invoices", ["issue_date"], unique=False)
    op.create_index(
        "ix_invoices_lifecycle_status",
        "invoices",
        ["lifecycle_status"],
        unique=False,
    )
    op.create_index(
        "ix_invoices_payment_status",
        "invoices",
        ["payment_status"],
        unique=False,
    )

    op.create_table(
        "invoice_lines",
        sa.Column(
            "id",
            sa.Uuid(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("invoice_id", sa.Uuid(), nullable=False),
        sa.Column("item_id", sa.Uuid(), nullable=True),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("quantity", sa.Numeric(precision=18, scale=4), nullable=False),
        sa.Column("unit_price", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column(
            "discount_percent",
            sa.Numeric(precision=5, scale=2),
            server_default=sa.text("0"),
            nullable=False,
        ),
        # -- REQUIERE VALIDACIÓN: contador/experto DIAN (tarifa y código de impuesto).
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
        sa.CheckConstraint("quantity > 0", name="ck_invoice_lines_quantity_positive"),
        sa.CheckConstraint("unit_price >= 0", name="ck_invoice_lines_unit_price_non_negative"),
        sa.CheckConstraint(
            "discount_percent >= 0 AND discount_percent <= 100",
            name="ck_invoice_lines_discount_percent_range",
        ),
        sa.CheckConstraint(
            "tax_rate >= 0 AND tax_rate <= 100",
            name="ck_invoice_lines_tax_rate_range",
        ),
        sa.CheckConstraint("line_subtotal >= 0", name="ck_invoice_lines_subtotal_non_negative"),
        sa.CheckConstraint("line_tax >= 0", name="ck_invoice_lines_tax_non_negative"),
        sa.CheckConstraint("line_total >= 0", name="ck_invoice_lines_total_non_negative"),
        sa.ForeignKeyConstraint(["invoice_id"], ["invoices.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["item_id"], ["items.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id", name="pk_invoice_lines"),
    )
    op.create_index("ix_invoice_lines_invoice_id", "invoice_lines", ["invoice_id"], unique=False)
    op.create_index("ix_invoice_lines_item_id", "invoice_lines", ["item_id"], unique=False)

    op.create_table(
        "payments",
        sa.Column(
            "id",
            sa.Uuid(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("invoice_id", sa.Uuid(), nullable=False),
        sa.Column("amount", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("payment_date", sa.Date(), nullable=False),
        # -- REQUIERE VALIDACIÓN: contador/experto DIAN (medios de pago).
        sa.Column("method", sa.String(length=50), nullable=False),
        sa.Column("reference", sa.String(length=100), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("amount > 0", name="ck_payments_amount_positive"),
        sa.ForeignKeyConstraint(["invoice_id"], ["invoices.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id", name="pk_payments"),
    )
    op.create_index("ix_payments_invoice_id", "payments", ["invoice_id"], unique=False)
    op.create_index("ix_payments_payment_date", "payments", ["payment_date"], unique=False)

    op.create_table(
        "number_sequences",
        sa.Column(
            "id",
            sa.Uuid(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("prefix", sa.String(length=20), nullable=False),
        sa.Column(
            "next_number",
            sa.BigInteger(),
            server_default=sa.text("1"),
            nullable=False,
        ),
        sa.Column("version", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.CheckConstraint("next_number > 0", name="ck_number_sequences_next_number_positive"),
        sa.PrimaryKeyConstraint("id", name="pk_number_sequences"),
        sa.UniqueConstraint("name", name="uq_number_sequences_name"),
    )

    op.create_table(
        "idempotency_keys",
        sa.Column(
            "id",
            sa.Uuid(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("key", sa.String(length=255), nullable=False),
        sa.Column("request_hash", sa.String(length=64), nullable=False),
        sa.Column("response_body", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_idempotency_keys"),
        sa.UniqueConstraint("key", name="uq_idempotency_keys_key"),
    )
    op.create_index(
        "ix_idempotency_keys_created_at",
        "idempotency_keys",
        ["created_at"],
        unique=False,
    )

    # Comentarios SQL visibles para revisores y herramientas de introspección.
    op.execute(
        "COMMENT ON COLUMN contacts.tax_id IS "
        "'REQUIERE VALIDACIÓN: contador/experto DIAN. "
        "Formato y validación de identificación fiscal.'"
    )
    op.execute(
        "COMMENT ON COLUMN taxes.rate IS "
        "'REQUIERE VALIDACIÓN: contador/experto DIAN. "
        "Tarifa 0-100 con 4 decimales y catálogo de impuestos.'"
    )
    op.execute(
        "COMMENT ON COLUMN invoices.number IS "
        "'REQUIERE VALIDACIÓN: contador/experto DIAN. Numeración autorizada, prefijo y rango.'"
    )
    op.execute(
        "COMMENT ON COLUMN invoices.issue_date IS "
        "'REQUIERE VALIDACIÓN: contador/experto DIAN. Reglas de fecha de emisión.'"
    )
    op.execute(
        "COMMENT ON COLUMN invoices.currency IS "
        "'MVP solo COP. REQUIERE VALIDACIÓN: contador/experto DIAN para multimoneda.'"
    )
    op.execute(
        "COMMENT ON COLUMN invoice_lines.discount_percent IS "
        "'REQUIERE VALIDACIÓN: contador/experto DIAN. Efecto del descuento en la base gravable.'"
    )
    op.execute(
        "COMMENT ON COLUMN invoice_lines.tax_rate IS "
        "'REQUIERE VALIDACIÓN: contador/experto DIAN. Tarifa y código de impuesto.'"
    )
    op.execute(
        "COMMENT ON COLUMN payments.method IS "
        "'REQUIERE VALIDACIÓN: contador/experto DIAN. Catálogo de medios de pago.'"
    )


def downgrade() -> None:
    op.drop_table("idempotency_keys")
    op.drop_table("number_sequences")
    op.drop_table("payments")
    op.drop_table("invoice_lines")
    op.drop_table("invoices")
    op.drop_table("items")
    op.drop_table("contacts")
    op.drop_table("taxes")

    lifecycle_status_enum.drop(op.get_bind(), checkfirst=True)
    payment_status_enum.drop(op.get_bind(), checkfirst=True)
