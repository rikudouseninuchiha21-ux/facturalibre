"""Notificaciones in-app por usuario.

Revision ID: 20261024_0024
Revises: 20261024_0023
Create Date: 2026-10-25

Crea la tabla ``notifications`` para las notificaciones in-app generadas por
eventos del dominio (alertas de presupuesto, aprobación y cierre automático).

El ``user_id`` usa ON DELETE CASCADE: al eliminar el usuario se eliminan sus
notificaciones. La severidad es un ENUM nativo ``notification_severity``
(INFO/WARNING/CRITICAL), siguiendo la convención de enums del proyecto.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "20261024_0024"
down_revision: str | None = "20261024_0023"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# create_type=False evita que el CREATE TABLE intente crear el ENUM una segunda
# vez; el tipo se crea explícitamente en upgrade() (patrón de 0017/0023).
notification_severity_enum = postgresql.ENUM(
    "INFO",
    "WARNING",
    "CRITICAL",
    name="notification_severity",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    notification_severity_enum.create(bind, checkfirst=True)

    op.create_table(
        "notifications",
        sa.Column(
            "id",
            sa.Uuid(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("category", sa.String(length=30), nullable=False),
        sa.Column(
            "severity",
            notification_severity_enum,
            nullable=False,
        ),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("body", sa.Text(), nullable=True),
        sa.Column("link", sa.String(length=500), nullable=True),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_notifications"),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
    )
    op.create_index("ix_notifications_category", "notifications", ["category"])
    op.create_index(
        "ix_notifications_user_read_at",
        "notifications",
        ["user_id", "read_at"],
    )
    op.create_index(
        "ix_notifications_user_created",
        "notifications",
        ["user_id", "created_at"],
    )
    op.create_index("ix_notifications_created_at", "notifications", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_notifications_created_at", table_name="notifications")
    op.drop_index("ix_notifications_user_created", table_name="notifications")
    op.drop_index("ix_notifications_user_read_at", table_name="notifications")
    op.drop_index("ix_notifications_category", table_name="notifications")
    op.drop_table("notifications")

    notification_severity_enum.drop(bind=op.get_bind(), checkfirst=True)
