"""Conciliación bancaria: vínculo entre pagos/gastos y movimientos.

Revision ID: 20261024_0019
Revises: 20261024_0018
Create Date: 2026-10-24

El módulo de tesorería ya cuenta con ``bank_transactions.is_reconciled`` y
``reconciled_at`` para marcar el movimiento contra el extracto. Esta migración
agrega el vínculo explícito desde las transacciones del sistema:

- ``payments.bank_movement_id``: pago de cliente conciliado.
- ``expenses.bank_movement_id``: gasto conciliado.

La FK apunta a ``bank_transactions.id`` y usa ``ON DELETE SET NULL`` para que
el vínculo no impida una eventual depuración del movimiento bancario. La
unicidad del vínculo se valida en la capa de aplicación porque un mismo
movimiento no debe quedar asociado a un pago y a un gasto a la vez.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20261024_0019"
down_revision: str | None = "20261024_0018"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "payments",
        sa.Column(
            "bank_movement_id",
            sa.Uuid(),
            nullable=True,
            comment="Movimiento bancario conciliado con este pago.",
        ),
    )
    op.create_index(
        "ix_payments_bank_movement_id",
        "payments",
        ["bank_movement_id"],
    )
    op.create_foreign_key(
        "fk_payments_bank_movement_id_bank_transactions",
        "payments",
        "bank_transactions",
        ["bank_movement_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.add_column(
        "expenses",
        sa.Column(
            "bank_movement_id",
            sa.Uuid(),
            nullable=True,
            comment="Movimiento bancario conciliado con este gasto.",
        ),
    )
    op.create_index(
        "ix_expenses_bank_movement_id",
        "expenses",
        ["bank_movement_id"],
    )
    op.create_foreign_key(
        "fk_expenses_bank_movement_id_bank_transactions",
        "expenses",
        "bank_transactions",
        ["bank_movement_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_expenses_bank_movement_id_bank_transactions",
        "expenses",
        type_="foreignkey",
    )
    op.drop_index("ix_expenses_bank_movement_id", table_name="expenses")
    op.drop_column("expenses", "bank_movement_id")

    op.drop_constraint(
        "fk_payments_bank_movement_id_bank_transactions",
        "payments",
        type_="foreignkey",
    )
    op.drop_index("ix_payments_bank_movement_id", table_name="payments")
    op.drop_column("payments", "bank_movement_id")
