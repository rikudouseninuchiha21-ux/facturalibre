"""Pagos a compras: tabla de pagos a proveedores.

Revision ID: 20261023_0009
Revises: 20261023_0008
Create Date: 2026-10-23

Crea la tabla ``purchase_payments`` para registrar los pagos realizados a
facturas de compra (Cuentas por Pagar) y extiende el enum
``accounting_entry_source_type`` con el valor ``PURCHASE_PAYMENT`` para los
asientos contables de pago a proveedores.

REQUIERE VALIDACIÓN: contador/experto DIAN para los asientos contables de pago
a compras (débito a Cuentas por Pagar, crédito a Bancos/Caja).
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20261023_0009"
down_revision: str | None = "20261023_0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Extender enum de origen de asientos con PURCHASE_PAYMENT.
    op.execute("ALTER TYPE accounting_entry_source_type ADD VALUE IF NOT EXISTS 'PURCHASE_PAYMENT'")

    op.create_table(
        "purchase_payments",
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
            "amount",
            sa.Numeric(precision=18, scale=2),
            nullable=False,
        ),
        sa.Column("payment_date", sa.Date(), nullable=False),
        sa.Column("method", sa.String(length=50), nullable=False),
        sa.Column("reference", sa.String(length=100), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "amount > 0",
            name="ck_purchase_payments_amount_positive",
        ),
        sa.ForeignKeyConstraint(
            ["purchase_invoice_id"],
            ["purchase_invoices.id"],
            name="fk_purchase_payments_purchase_invoice_id_purchase_invoices",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_purchase_payments"),
    )
    op.create_index(
        "ix_purchase_payments_purchase_invoice_id",
        "purchase_payments",
        ["purchase_invoice_id"],
        unique=False,
    )
    op.create_index(
        "ix_purchase_payments_payment_date",
        "purchase_payments",
        ["payment_date"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_purchase_payments_payment_date", table_name="purchase_payments")
    op.drop_index(
        "ix_purchase_payments_purchase_invoice_id",
        table_name="purchase_payments",
    )
    op.drop_table("purchase_payments")
