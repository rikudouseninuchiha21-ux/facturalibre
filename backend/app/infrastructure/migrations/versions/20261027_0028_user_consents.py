"""Tabla de consentimientos GDPR/CCPA (Fase 39B).

Revision ID: 20261027_0028
Revises: 20261027_0027
Create Date: 2026-10-27

``user_consents`` es un registro inmutable de auditoría: cada fila es un
consentimiento (o rechazo) con IP, user-agent y marca de tiempo.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261027_0028"
down_revision: str | None = "20261027_0027"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "user_consents",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("user_agent", sa.String(255), nullable=True),
        sa.Column("consent_type", sa.String(30), nullable=False),
        sa.Column("is_granted", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_user_consents"),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_user_consents_user_id",
            ondelete="SET NULL",
        ),
    )
    op.create_index("ix_user_consents_user_id", "user_consents", ["user_id"])
    op.create_index("ix_user_consents_consent_type", "user_consents", ["consent_type"])


def downgrade() -> None:
    op.drop_index("ix_user_consents_consent_type", table_name="user_consents")
    op.drop_index("ix_user_consents_user_id", table_name="user_consents")
    op.drop_table("user_consents")
