"""Ítems: columna price_includes_tax para precios con/sin IVA incluido.

Revision ID: 20261024_0015
Revises: 20261024_0014
Create Date: 2026-10-24

Añade la columna ``price_includes_tax`` (BOOLEAN, default FALSE) a la tabla
``items``. Cuando es TRUE, el precio unitario del ítem ya incluye el impuesto
y el backend debe calcular la base gravable descontando el IVA
(precio / (1 + tasa)).

REQUIERE VALIDACIÓN: contador/experto DIAN para el tratamiento de precios
con IVA incluido.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20261024_0015"
down_revision: str | None = "20261024_0013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "items",
        sa.Column(
            "price_includes_tax",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )


def downgrade() -> None:
    op.drop_column("items", "price_includes_tax")
