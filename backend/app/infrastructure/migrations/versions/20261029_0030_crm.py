"""CRM: etapas del embudo, oportunidades y actividades.

Revision ID: 20261029_0030
Revises: 20261028_0029
Create Date: 2026-10-29
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20261029_0030"
down_revision: str | None = "20261028_0029"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

DEFAULT_STAGES: tuple[tuple[str, int, str, bool, bool], ...] = (
    ("Nuevo Lead", 1, "#94a3b8", False, False),
    ("Contactado", 2, "#3b82f6", False, False),
    ("Propuesta", 3, "#8b5cf6", False, False),
    ("Negociación", 4, "#f59e0b", False, False),
    ("Ganado", 5, "#10b981", True, False),
    ("Perdido", 6, "#ef4444", False, True),
)


def upgrade() -> None:
    op.create_table(
        "crm_stages",
        sa.Column(
            "id",
            sa.Uuid(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("company_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("order", sa.Integer(), nullable=False),
        sa.Column(
            "color",
            sa.String(length=7),
            server_default=sa.text("'#7c3aed'"),
            nullable=False,
        ),
        sa.Column(
            "is_won",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column(
            "is_lost",
            sa.Boolean(),
            server_default=sa.text("false"),
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
        sa.CheckConstraint(
            "NOT (is_won AND is_lost)",
            name="ck_crm_stages_one_outcome",
        ),
        sa.ForeignKeyConstraint(
            ["company_id"],
            ["companies.id"],
            name="fk_crm_stages_company_id_companies",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_crm_stages"),
    )
    op.create_index("ix_crm_stages_company_id", "crm_stages", ["company_id"])
    op.create_index("ix_crm_stages_order", "crm_stages", ["order"])

    op.create_table(
        "crm_opportunities",
        sa.Column(
            "id",
            sa.Uuid(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("company_id", sa.Uuid(), nullable=False),
        sa.Column("contact_id", sa.Uuid(), nullable=False),
        sa.Column("stage_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column(
            "amount",
            sa.Numeric(precision=18, scale=2),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column("expected_close_date", sa.Date(), nullable=True),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("quote_id", sa.Uuid(), nullable=True),
        sa.Column("invoice_id", sa.Uuid(), nullable=True),
        sa.Column(
            "is_won",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column(
            "is_lost",
            sa.Boolean(),
            server_default=sa.text("false"),
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
        sa.CheckConstraint(
            "amount >= 0",
            name="ck_crm_opportunities_amount_non_negative",
        ),
        sa.CheckConstraint(
            "NOT (is_won AND is_lost)",
            name="ck_crm_opportunities_one_outcome",
        ),
        sa.ForeignKeyConstraint(
            ["company_id"],
            ["companies.id"],
            name="fk_crm_opportunities_company_id_companies",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["contact_id"],
            ["contacts.id"],
            name="fk_crm_opportunities_contact_id_contacts",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["stage_id"],
            ["crm_stages.id"],
            name="fk_crm_opportunities_stage_id_crm_stages",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["owner_id"],
            ["users.id"],
            name="fk_crm_opportunities_owner_id_users",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["quote_id"],
            ["quotes.id"],
            name="fk_crm_opportunities_quote_id_quotes",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["invoice_id"],
            ["invoices.id"],
            name="fk_crm_opportunities_invoice_id_invoices",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_crm_opportunities"),
    )
    op.create_index("ix_crm_opportunities_company_id", "crm_opportunities", ["company_id"])
    op.create_index("ix_crm_opportunities_contact_id", "crm_opportunities", ["contact_id"])
    op.create_index("ix_crm_opportunities_stage_id", "crm_opportunities", ["stage_id"])
    op.create_index("ix_crm_opportunities_owner_id", "crm_opportunities", ["owner_id"])
    op.create_index("ix_crm_opportunities_quote_id", "crm_opportunities", ["quote_id"])
    op.create_index("ix_crm_opportunities_invoice_id", "crm_opportunities", ["invoice_id"])

    op.create_table(
        "crm_activities",
        sa.Column(
            "id",
            sa.Uuid(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("company_id", sa.Uuid(), nullable=False),
        sa.Column("opportunity_id", sa.Uuid(), nullable=False),
        sa.Column("type", sa.String(length=20), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column(
            "activity_date",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "type IN ('CALL', 'EMAIL', 'MEETING', 'NOTE')",
            name="ck_crm_activities_type",
        ),
        sa.ForeignKeyConstraint(
            ["company_id"],
            ["companies.id"],
            name="fk_crm_activities_company_id_companies",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["opportunity_id"],
            ["crm_opportunities.id"],
            name="fk_crm_activities_opportunity_id_crm_opportunities",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["users.id"],
            name="fk_crm_activities_created_by_users",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_crm_activities"),
    )
    op.create_index("ix_crm_activities_company_id", "crm_activities", ["company_id"])
    op.create_index("ix_crm_activities_opportunity_id", "crm_activities", ["opportunity_id"])
    op.create_index("ix_crm_activities_activity_date", "crm_activities", ["activity_date"])
    op.create_index("ix_crm_activities_created_by", "crm_activities", ["created_by"])

    bind = op.get_bind()
    for name, order, color, is_won, is_lost in DEFAULT_STAGES:
        bind.execute(
            sa.text(
                "INSERT INTO crm_stages "
                '(company_id, name, "order", color, is_won, is_lost) '
                "SELECT id, :name, :order, :color, :is_won, :is_lost FROM companies"
            ),
            {
                "name": name,
                "order": order,
                "color": color,
                "is_won": is_won,
                "is_lost": is_lost,
            },
        )


def downgrade() -> None:
    op.drop_table("crm_activities")
    op.drop_table("crm_opportunities")
    op.drop_table("crm_stages")
