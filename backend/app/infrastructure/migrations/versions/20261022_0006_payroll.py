"""Nómina: empleados, periodos y detalle de liquidación.

Revision ID: 20261022_0006
Revises: 20261022_0005
Create Date: 2026-10-22

La migración crea el núcleo de nómina y prepara la integración contable:
agrega ``PAYROLL`` al ENUM de origen de asientos y siembra las cuentas PUC
necesarias (510506, 250505 y 237005) con sus cuentas padre.

REQUIERE VALIDACIÓN: contador público colombiano. Las cuentas, los porcentajes
de salud y pensión, los topes legales y los parafiscales son valores iniciales
del MVP; deben confirmarse contra la normativa vigente y el PUC de la empresa.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "20261022_0006"
down_revision: str | None = "20261022_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


payroll_period_status_enum = postgresql.ENUM(
    "DRAFT",
    "CLOSED",
    name="payroll_period_status",
    create_type=False,
)


# Cuentas adicionales necesarias para el asiento automático de nómina.
# Los padres se siembran primero para respetar la FK jerárquica del PUC.
PAYROLL_PUC_SEED: tuple[dict[str, str | None], ...] = (
    {
        "code": "5",
        "name": "Gastos",
        "account_type": "GASTO",
        "nature": "DEBITO",
        "parent_code": None,
    },
    {
        "code": "51",
        "name": "Gastos operacionales",
        "account_type": "GASTO",
        "nature": "DEBITO",
        "parent_code": "5",
    },
    {
        "code": "5105",
        "name": "Gastos de administración",
        "account_type": "GASTO",
        "nature": "DEBITO",
        "parent_code": "51",
    },
    {
        "code": "510506",
        "name": "Sueldos",
        "account_type": "GASTO",
        "nature": "DEBITO",
        "parent_code": "5105",
    },
    {
        "code": "23",
        "name": "Cuentas por pagar",
        "account_type": "PASIVO",
        "nature": "CREDITO",
        "parent_code": "2",
    },
    {
        "code": "2370",
        "name": "Retenciones y aportes de nómina",
        "account_type": "PASIVO",
        "nature": "CREDITO",
        "parent_code": "23",
    },
    {
        "code": "237005",
        "name": "Aportes a salud y pensión",
        "account_type": "PASIVO",
        "nature": "CREDITO",
        "parent_code": "2370",
    },
    {
        "code": "25",
        "name": "Obligaciones laborales",
        "account_type": "PASIVO",
        "nature": "CREDITO",
        "parent_code": "2",
    },
    {
        "code": "2505",
        "name": "Salarios por pagar",
        "account_type": "PASIVO",
        "nature": "CREDITO",
        "parent_code": "25",
    },
    {
        "code": "250505",
        "name": "Salarios por pagar",
        "account_type": "PASIVO",
        "nature": "CREDITO",
        "parent_code": "2505",
    },
)


def upgrade() -> None:
    bind = op.get_bind()
    payroll_period_status_enum.create(bind, checkfirst=True)

    # El valor se agrega de forma idempotente. En PostgreSQL 12+ puede
    # ejecutarse dentro de la transacción de Alembic, pero no puede usarse en
    # la misma transacción que lo crea. Esta migración no inserta asientos.
    op.execute("ALTER TYPE accounting_entry_source_type ADD VALUE IF NOT EXISTS 'PAYROLL'")

    op.create_table(
        "employees",
        sa.Column(
            "id",
            sa.Uuid(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("document", sa.String(length=30), nullable=False),
        sa.Column("first_name", sa.String(length=100), nullable=False),
        sa.Column("last_name", sa.String(length=100), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("base_salary", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
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
        sa.CheckConstraint(
            "base_salary > 0",
            name="ck_employees_base_salary_positive",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_employees"),
        sa.UniqueConstraint("document", name="uq_employees_document"),
    )
    op.create_index(
        "ix_employees_is_active",
        "employees",
        ["is_active"],
        unique=False,
    )

    op.create_table(
        "payroll_periods",
        sa.Column(
            "id",
            sa.Uuid(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("month", sa.Integer(), nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            payroll_period_status_enum,
            server_default=sa.text("'DRAFT'"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "month BETWEEN 1 AND 12",
            name="ck_payroll_periods_month_range",
        ),
        sa.CheckConstraint(
            "year BETWEEN 2000 AND 2100",
            name="ck_payroll_periods_year_range",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_payroll_periods"),
        sa.UniqueConstraint(
            "month",
            "year",
            name="uq_payroll_periods_month_year",
        ),
    )
    op.create_index(
        "ix_payroll_periods_status",
        "payroll_periods",
        ["status"],
        unique=False,
    )

    op.create_table(
        "payroll_details",
        sa.Column(
            "id",
            sa.Uuid(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("period_id", sa.Uuid(), nullable=False),
        sa.Column("employee_id", sa.Uuid(), nullable=False),
        sa.Column("base_salary", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column(
            "health_deduction",
            sa.Numeric(precision=18, scale=2),
            nullable=False,
        ),
        sa.Column(
            "pension_deduction",
            sa.Numeric(precision=18, scale=2),
            nullable=False,
        ),
        sa.Column("net_pay", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "base_salary > 0",
            name="ck_payroll_details_base_salary_positive",
        ),
        sa.CheckConstraint(
            "health_deduction >= 0",
            name="ck_payroll_details_health_deduction_non_negative",
        ),
        sa.CheckConstraint(
            "pension_deduction >= 0",
            name="ck_payroll_details_pension_deduction_non_negative",
        ),
        sa.CheckConstraint(
            "net_pay >= 0",
            name="ck_payroll_details_net_pay_non_negative",
        ),
        sa.ForeignKeyConstraint(
            ["period_id"],
            ["payroll_periods.id"],
            name="fk_payroll_details_period_id_payroll_periods",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["employee_id"],
            ["employees.id"],
            name="fk_payroll_details_employee_id_employees",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_payroll_details"),
        sa.UniqueConstraint(
            "period_id",
            "employee_id",
            name="uq_payroll_details_period_id_employee_id",
        ),
    )
    op.create_index(
        "ix_payroll_details_period_id",
        "payroll_details",
        ["period_id"],
        unique=False,
    )
    op.create_index(
        "ix_payroll_details_employee_id",
        "payroll_details",
        ["employee_id"],
        unique=False,
    )

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
    for account in PAYROLL_PUC_SEED:
        bind.execute(insert_account, account)

    op.execute(
        "COMMENT ON TABLE employees IS "
        "'REQUIERE VALIDACIÓN: datos laborales y aportes según normativa colombiana.'"
    )
    op.execute(
        "COMMENT ON COLUMN employees.base_salary IS "
        "'REQUIERE VALIDACIÓN: salario base y topes de ley.'"
    )
    op.execute(
        "COMMENT ON TABLE payroll_periods IS "
        "'Periodo mensual de nómina. Al calcularlo pasa de DRAFT a CLOSED.'"
    )
    op.execute(
        "COMMENT ON COLUMN payroll_details.health_deduction IS "
        "'REQUIERE VALIDACIÓN: porcentaje de salud, topes y exoneraciones.'"
    )
    op.execute(
        "COMMENT ON COLUMN payroll_details.pension_deduction IS "
        "'REQUIERE VALIDACIÓN: porcentaje de pensión, topes y fondo elegido.'"
    )


def downgrade() -> None:
    op.drop_table("payroll_details")
    op.drop_table("payroll_periods")
    op.drop_table("employees")

    payroll_period_status_enum.drop(op.get_bind(), checkfirst=True)

    # El valor PAYROLL del ENUM de contabilidad y las cuentas PUC sembradas se
    # conservan deliberadamente: eliminarlos podría romper asientos históricos
    # y PostgreSQL no permite quitar valores de un ENUM de forma simple.
