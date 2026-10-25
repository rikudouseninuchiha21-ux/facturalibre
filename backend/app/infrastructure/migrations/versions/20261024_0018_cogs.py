"""Costo de ventas: cuentas PUC para el asiento de COGS.

Revision ID: 20261024_0018
Revises: 20261024_0017
Create Date: 2026-10-24

Siembra la jerarquía 6/61/6135 del PUC colombiano para poder debitar el costo
de mercancías vendidas al emitir una factura. El crédito correspondiente se
hace contra la cuenta de inventario 1435, ya sembrada por la migración de
compras.

REQUIERE VALIDACIÓN: contador público colombiano. La cuenta 6135 y su nombre
son una configuración inicial del MVP y deben confirmarse contra el PUC de la
empresa.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20261024_0018"
down_revision: str | None = "20261024_0017"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


COGS_PUC_SEED: tuple[dict[str, str | None], ...] = (
    {
        "code": "6",
        "name": "Costos de ventas y de prestación de servicios",
        "account_type": "COSTO",
        "nature": "DEBITO",
        "parent_code": None,
    },
    {
        "code": "61",
        "name": "Costo de ventas y de prestación de servicios",
        "account_type": "COSTO",
        "nature": "DEBITO",
        "parent_code": "6",
    },
    {
        "code": "6135",
        "name": "Costo de mercancías vendidas",
        "account_type": "COSTO",
        "nature": "DEBITO",
        "parent_code": "61",
    },
)


def upgrade() -> None:
    connection = op.get_bind()
    insert_account = sa.text(
        """
        INSERT INTO accounting_accounts
            (code, name, account_type, nature, parent_code)
        VALUES
            (:code, :name,
             CAST(:account_type AS accounting_account_type),
             CAST(:nature AS accounting_account_nature),
             :parent_code)
        ON CONFLICT (code) DO NOTHING
        """
    )
    for account in COGS_PUC_SEED:
        connection.execute(insert_account, account)


def downgrade() -> None:
    # La FK de accounting_entry_lines impide borrar cuentas con movimientos.
    # Si existen asientos de COGS, el operador debe revertirlos o depurar la
    # contabilidad antes de ejecutar este downgrade.
    op.execute("DELETE FROM accounting_accounts WHERE code IN ('6135', '61', '6')")
