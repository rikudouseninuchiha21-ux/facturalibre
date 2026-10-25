"""Patrimonio: cuentas PUC de capital social y asiento de aporte inicial.

Revision ID: 20261024_0022
Revises: 20261024_0021
Create Date: 2026-10-25

Siembra la jerarquía 3/31/3105 del PUC colombiano para poder acreditar el
capital suscrito y pagado. El asiento de aporte (débito a Bancos, crédito a
3105) se registra mediante POST /api/v1/accounting/initial-capital.

REQUIERE VALIDACIÓN: contador público colombiano. Las cuentas 3, 31 y 3105 y
sus nombres son la configuración inicial del MVP y deben confirmarse contra el
PUC de la empresa.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20261024_0022"
down_revision: str | None = "20261024_0021"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


EQUITY_PUC_SEED: tuple[dict[str, str | None], ...] = (
    {
        "code": "3",
        "name": "Patrimonio",
        "account_type": "PATRIMONIO",
        "nature": "CREDITO",
        "parent_code": None,
    },
    {
        "code": "31",
        "name": "Capital social",
        "account_type": "PATRIMONIO",
        "nature": "CREDITO",
        "parent_code": "3",
    },
    {
        "code": "3105",
        "name": "Capital suscrito y pagado",
        "account_type": "PATRIMONIO",
        "nature": "CREDITO",
        "parent_code": "31",
    },
)


def upgrade() -> None:
    # PostgreSQL permite agregar el valor dentro de la transacción de Alembic,
    # pero no usarlo en la misma transacción. Esta migración no inserta
    # asientos con el nuevo valor.
    op.execute("ALTER TYPE accounting_entry_source_type ADD VALUE IF NOT EXISTS 'INITIAL_CAPITAL'")

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
    for account in EQUITY_PUC_SEED:
        connection.execute(insert_account, account)


def downgrade() -> None:
    # La FK de accounting_entry_lines impide borrar cuentas con movimientos.
    # Si ya hay asientos de capital, el operador debe revertirlos o depurar
    # la contabilidad antes de ejecutar este downgrade.
    op.execute("DELETE FROM accounting_accounts WHERE code IN ('3105', '31', '3')")
