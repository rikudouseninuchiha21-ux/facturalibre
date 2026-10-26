"""Cartera: recordatorios de cobranza y acuerdos de pago.

Revision ID: 20261025_0025
Revises: 20261024_0024
Create Date: 2026-10-25

Crea las tablas ``payment_reminders``, ``payment_agreements`` y
``payment_agreement_installments`` para la gestión de cuentas por cobrar.

Decisiones:
- ``due_date`` ya existía en ``invoices``; no se agrega ninguna columna. El
  aging usa ``due_date`` y, solo si falta, ``issue_date + 30 días``.
- ``channel`` y ``status`` usan ENUM nativo de PostgreSQL (patrón del
  proyecto para estados), no VARCHAR + CHECK.
- Los acuerdos son instrumentos de gestión: no crean asientos contables ni
  tablas de saldos. El aging se calcula en lectura.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "20261025_0025"
down_revision: str | None = "20261024_0024"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


reminder_channel_enum = postgresql.ENUM(
    "IN_APP",
    "EMAIL",
    "SMS",
    "CALL",
    name="payment_reminder_channel",
    create_type=False,
)

agreement_status_enum = postgresql.ENUM(
    "ACTIVE",
    "COMPLETED",
    "BROKEN",
    "CANCELLED",
    name="payment_agreement_status",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    reminder_channel_enum.create(bind, checkfirst=True)
    agreement_status_enum.create(bind, checkfirst=True)

    op.create_table(
        "payment_reminders",
        sa.Column(
            "id",
            sa.Uuid(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("invoice_id", sa.Uuid(), nullable=False),
        sa.Column("contact_id", sa.Uuid(), nullable=False),
        sa.Column("level", sa.Integer(), nullable=False),
        sa.Column(
            "channel",
            reminder_channel_enum,
            server_default=sa.text("'IN_APP'"),
            nullable=False,
        ),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("level BETWEEN 1 AND 5", name="ck_payment_reminders_level_range"),
        sa.PrimaryKeyConstraint("id", name="pk_payment_reminders"),
        sa.ForeignKeyConstraint(
            ["invoice_id"],
            ["invoices.id"],
            name="fk_payment_reminders_invoice_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["contact_id"],
            ["contacts.id"],
            name="fk_payment_reminders_contact_id",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["users.id"],
            name="fk_payment_reminders_created_by",
            ondelete="RESTRICT",
        ),
    )
    op.create_index(
        "ix_payment_reminders_invoice_sent",
        "payment_reminders",
        ["invoice_id", "sent_at"],
    )
    op.create_index(
        "ix_payment_reminders_contact_id",
        "payment_reminders",
        ["contact_id"],
    )

    op.create_table(
        "payment_agreements",
        sa.Column(
            "id",
            sa.Uuid(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("contact_id", sa.Uuid(), nullable=False),
        sa.Column("invoice_id", sa.Uuid(), nullable=True),
        sa.Column("total_amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("installments", sa.Integer(), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column(
            "status",
            agreement_status_enum,
            server_default=sa.text("'ACTIVE'"),
            nullable=False,
        ),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_by", sa.Uuid(), nullable=False),
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
        sa.CheckConstraint(
            "total_amount >= 0",
            name="ck_payment_agreements_total_non_negative",
        ),
        sa.CheckConstraint(
            "installments >= 1",
            name="ck_payment_agreements_installments_positive",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_payment_agreements"),
        sa.ForeignKeyConstraint(
            ["contact_id"],
            ["contacts.id"],
            name="fk_payment_agreements_contact_id",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["invoice_id"],
            ["invoices.id"],
            name="fk_payment_agreements_invoice_id",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["users.id"],
            name="fk_payment_agreements_created_by",
            ondelete="RESTRICT",
        ),
    )
    op.create_index(
        "ix_payment_agreements_contact_status",
        "payment_agreements",
        ["contact_id", "status"],
    )
    op.create_index(
        "ix_payment_agreements_invoice_id",
        "payment_agreements",
        ["invoice_id"],
    )
    op.create_index(
        "ix_payment_agreements_status",
        "payment_agreements",
        ["status"],
    )

    op.create_table(
        "payment_agreement_installments",
        sa.Column(
            "id",
            sa.Uuid(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("agreement_id", sa.Uuid(), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=False),
        sa.Column("amount", sa.Numeric(18, 2), nullable=False),
        sa.Column(
            "paid_amount",
            sa.Numeric(18, 2),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "amount >= 0",
            name="ck_agreement_installments_amount_non_negative",
        ),
        sa.CheckConstraint(
            "paid_amount >= 0",
            name="ck_agreement_installments_paid_non_negative",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_payment_agreement_installments"),
        sa.ForeignKeyConstraint(
            ["agreement_id"],
            ["payment_agreements.id"],
            name="fk_agreement_installments_agreement_id",
            ondelete="CASCADE",
        ),
    )
    op.create_index(
        "ix_payment_agreement_installments_agreement_id",
        "payment_agreement_installments",
        ["agreement_id"],
    )
    op.create_index(
        "ix_payment_agreement_installments_due_date",
        "payment_agreement_installments",
        ["due_date"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_payment_agreement_installments_due_date",
        table_name="payment_agreement_installments",
    )
    op.drop_index(
        "ix_payment_agreement_installments_agreement_id",
        table_name="payment_agreement_installments",
    )
    op.drop_table("payment_agreement_installments")

    op.drop_index("ix_payment_agreements_status", table_name="payment_agreements")
    op.drop_index("ix_payment_agreements_invoice_id", table_name="payment_agreements")
    op.drop_index("ix_payment_agreements_contact_status", table_name="payment_agreements")
    op.drop_table("payment_agreements")

    op.drop_index("ix_payment_reminders_contact_id", table_name="payment_reminders")
    op.drop_index("ix_payment_reminders_invoice_sent", table_name="payment_reminders")
    op.drop_table("payment_reminders")

    agreement_status_enum.drop(bind=op.get_bind(), checkfirst=True)
    reminder_channel_enum.drop(bind=op.get_bind(), checkfirst=True)
