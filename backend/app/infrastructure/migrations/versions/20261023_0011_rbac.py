"""Control de acceso basado en roles (RBAC).

Revision ID: 20261023_0011
Revises: 20261023_0010
Create Date: 2026-10-23

Añade la columna ``role`` (ENUM: ADMIN, ACCOUNTANT, CASHIER) a la tabla
``users`` con valor por defecto ADMIN para no romper el usuario existente.

REQUIERE VALIDACIÓN: definir la matriz de permisos exacta por rol antes de
desplegar en producción.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20261023_0011"
down_revision: str | None = "20261023_0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

user_role_enum = sa.Enum(
    "ADMIN",
    "ACCOUNTANT",
    "CASHIER",
    name="user_role",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    user_role_enum.create(bind, checkfirst=True)

    op.add_column(
        "users",
        sa.Column(
            "role",
            user_role_enum,
            nullable=False,
            server_default=sa.text("'ADMIN'"),
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "role")
    user_role_enum.drop(op.get_bind(), checkfirst=True)
