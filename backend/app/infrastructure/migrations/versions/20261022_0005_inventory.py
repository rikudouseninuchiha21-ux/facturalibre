"""Inventario: bodegas, movimientos de stock y saldos por bodega.

Revision ID: 20261022_0005
Revises: 20261022_0004
Create Date: 2026-10-22

El libro de movimientos es la fuente de verdad; ``stock_balances`` es una
proyección por ítem y bodega que el servicio mantiene en la misma transacción.
No se agrega una columna de stock editable al ítem.

REQUIERE VALIDACIÓN: la política de costeo y la regla para decidir si un ítem es
inventariable. En este MVP se asume que todo ítem de factura descuenta stock.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "20261022_0005"
down_revision: str | None = "20261022_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


movement_type_enum = postgresql.ENUM(
    "IN",
    "OUT",
    "TRANSFER_IN",
    "TRANSFER_OUT",
    "ADJUSTMENT",
    name="stock_movement_type",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    movement_type_enum.create(bind, checkfirst=True)

    op.create_table(
        "warehouses",
        sa.Column(
            "id",
            sa.Uuid(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column(
            "is_active",
            sa.Boolean(),
            server_default=sa.text("true"),
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
        sa.PrimaryKeyConstraint("id", name="pk_warehouses"),
        sa.UniqueConstraint("code", name="uq_warehouses_code"),
    )
    op.create_index(
        "ix_warehouses_is_active",
        "warehouses",
        ["is_active"],
        unique=False,
    )

    op.create_table(
        "stock_movements",
        sa.Column(
            "id",
            sa.Uuid(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("item_id", sa.Uuid(), nullable=False),
        sa.Column("warehouse_id", sa.Uuid(), nullable=False),
        sa.Column("movement_type", movement_type_enum, nullable=False),
        sa.Column("quantity", sa.Numeric(precision=18, scale=4), nullable=False),
        sa.Column("unit_cost", sa.Numeric(precision=18, scale=4), nullable=True),
        sa.Column("reference", sa.String(length=100), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "quantity > 0",
            name="ck_stock_movements_quantity_positive",
        ),
        sa.CheckConstraint(
            "unit_cost IS NULL OR unit_cost >= 0",
            name="ck_stock_movements_unit_cost_non_negative",
        ),
        sa.ForeignKeyConstraint(
            ["item_id"],
            ["items.id"],
            name="fk_stock_movements_item_id_items",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["warehouse_id"],
            ["warehouses.id"],
            name="fk_stock_movements_warehouse_id_warehouses",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_stock_movements"),
    )
    op.create_index(
        "ix_stock_movements_item_id",
        "stock_movements",
        ["item_id"],
        unique=False,
    )
    op.create_index(
        "ix_stock_movements_warehouse_id",
        "stock_movements",
        ["warehouse_id"],
        unique=False,
    )
    op.create_index(
        "ix_stock_movements_movement_type",
        "stock_movements",
        ["movement_type"],
        unique=False,
    )
    op.create_index(
        "ix_stock_movements_created_at",
        "stock_movements",
        ["created_at"],
        unique=False,
    )

    op.create_table(
        "stock_balances",
        sa.Column("item_id", sa.Uuid(), nullable=False),
        sa.Column("warehouse_id", sa.Uuid(), nullable=False),
        sa.Column(
            "quantity",
            sa.Numeric(precision=18, scale=4),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "quantity >= 0",
            name="ck_stock_balances_quantity_non_negative",
        ),
        sa.ForeignKeyConstraint(
            ["item_id"],
            ["items.id"],
            name="fk_stock_balances_item_id_items",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["warehouse_id"],
            ["warehouses.id"],
            name="fk_stock_balances_warehouse_id_warehouses",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint(
            "item_id",
            "warehouse_id",
            name="pk_stock_balances",
        ),
    )
    op.create_index(
        "ix_stock_balances_warehouse_id",
        "stock_balances",
        ["warehouse_id"],
        unique=False,
    )

    op.execute(
        "COMMENT ON TABLE stock_movements IS "
        "'Libro de movimientos: fuente de verdad del inventario.'"
    )
    op.execute(
        "COMMENT ON TABLE stock_balances IS "
        "'Proyección reconstruible: saldo actual por ítem y bodega.'"
    )
    op.execute(
        "COMMENT ON COLUMN stock_movements.quantity IS "
        "'REQUIERE VALIDACIÓN: unidad de medida y política de redondeo.'"
    )
    op.execute(
        "COMMENT ON COLUMN stock_movements.unit_cost IS "
        "'REQUIERE VALIDACIÓN: método de costeo (promedio ponderado global o por bodega).'"
    )


def downgrade() -> None:
    op.drop_table("stock_balances")
    op.drop_table("stock_movements")
    op.drop_table("warehouses")

    movement_type_enum.drop(op.get_bind(), checkfirst=True)
