"""Configuración de la empresa.

Revision ID: 20261023_0012
Revises: 20261023_0011
Create Date: 2026-10-23

Crea la tabla company_settings para almacenar los datos de la empresa
utilizados en facturas y reportes.

REQUIERE VALIDACIÓN: contador/experto DIAN para los datos fiscales.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20261023_0012"
down_revision: str | None = "20261023_0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "company_settings",
        sa.Column(
            "id",
            sa.Uuid(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("tax_id", sa.String(length=30), nullable=True),
        sa.Column("address", sa.String(length=300), nullable=True),
        sa.Column("phone", sa.String(length=30), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("logo_url", sa.String(length=500), nullable=True),
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
        sa.PrimaryKeyConstraint("id", name="pk_company_settings"),
    )
    # Insertar fila por defecto
    op.execute(
        sa.text(
            "INSERT INTO company_settings (name, tax_id, address, phone, email, logo_url) "
            "VALUES ('Mi Empresa S.A.S.', NULL, NULL, NULL, NULL, NULL)"
        )
    )


def downgrade() -> None:
    op.drop_table("company_settings")
