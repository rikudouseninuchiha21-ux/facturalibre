"""Campos fiscales para la Nómina Electrónica DIAN (Fase 39A).

Revision ID: 20261027_0027
Revises: 20261026_0026
Create Date: 2026-10-27

Extiende empleados, periodos de nómina y crea ``payroll_contributions``
(aportes y provisiones por liquidación de empleado) para soportar el XML
UBL 2.1 de Nómina Electrónica (Decreto 1601 de 2020), la PILA y el
reporte UGPP.

Decisiones:
- ``payroll_periods.dian_status`` REUTILIZA el enum nativo
  ``dian_document_status`` de la migración 0026 (misma semántica del
  documento electrónico).
- ``employees.document`` ya existe como número único: se agrega
  ``document_type`` (CC, CE, NIT, PA) y no se duplica el número.
- Aportes en tabla nueva ``payroll_contributions`` (1:1 con
  ``payroll_details``); los NUMERIC son NOT NULL DEFAULT 0 para no romper
  liquidaciones históricas.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20261027_0027"
down_revision: str | None = "20261026_0026"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

EMPLOYEE_COLUMNS: tuple[tuple[str, sa.Column], ...] = (
    ("document_type", sa.Column("document_type", sa.String(10), nullable=True)),
    ("birth_date", sa.Column("birth_date", sa.Date(), nullable=True)),
    ("address", sa.Column("address", sa.String(200), nullable=True)),
    ("municipality_code", sa.Column("municipality_code", sa.String(5), nullable=True)),
    ("department_code", sa.Column("department_code", sa.String(2), nullable=True)),
    ("contract_type", sa.Column("contract_type", sa.String(20), nullable=True)),
    ("salary_type", sa.Column("salary_type", sa.String(20), nullable=True)),
    ("risk_level", sa.Column("risk_level", sa.String(5), nullable=True)),
    ("bank_account", sa.Column("bank_account", sa.String(50), nullable=True)),
    ("afp_code", sa.Column("afp_code", sa.String(20), nullable=True)),
    ("eps_code", sa.Column("eps_code", sa.String(20), nullable=True)),
    ("arl_code", sa.Column("arl_code", sa.String(20), nullable=True)),
    (
        "severance_fund_code",
        sa.Column("severance_fund_code", sa.String(20), nullable=True),
    ),
    (
        "compensation_fund_code",
        sa.Column("compensation_fund_code", sa.String(20), nullable=True),
    ),
)

PERIOD_COLUMNS: tuple[tuple[str, sa.Column], ...] = (
    ("dian_cune", sa.Column("dian_cune", sa.String(96), nullable=True)),
    (
        "dian_status",
        sa.Column("dian_status", sa.Enum(name="dian_document_status"), nullable=True),
    ),
    ("xml_generated_at", sa.Column("xml_generated_at", sa.DateTime(timezone=True), nullable=True)),
    ("payment_date", sa.Column("payment_date", sa.Date(), nullable=True)),
    ("notes_dian", sa.Column("notes_dian", sa.Text(), nullable=True)),
)


def _money_col(name: str) -> tuple[str, sa.Column]:
    """Columna NUMERIC(18,2) NOT NULL DEFAULT 0 de un aporte."""
    return (
        name,
        sa.Column(
            name,
            sa.Numeric(18, 2),
            nullable=False,
            server_default=sa.text("0"),
        ),
    )


CONTRIBUTION_COLUMNS: tuple[tuple[str, sa.Column], ...] = tuple(
    _money_col(name)
    for name in (
        "health_employee",
        "health_employer",
        "pension_employee",
        "pension_employer",
        "arl_employer",
        "compensation_fund",
        "icbf",
        "sena",
        "severance",
        "severance_interest",
        "vacation",
        "bonus",
    )
)

CONTRIBUTION_CHECKS: tuple[tuple[str, str], ...] = (
    ("ck_payroll_contributions_health_employer", "health_employer >= 0"),
    ("ck_payroll_contributions_health_employee", "health_employee >= 0"),
    ("ck_payroll_contributions_pension_employer", "pension_employer >= 0"),
    ("ck_payroll_contributions_pension_employee", "pension_employee >= 0"),
    ("ck_payroll_contributions_arl", "arl_employer >= 0"),
    ("ck_payroll_contributions_compensation_fund", "compensation_fund >= 0"),
    ("ck_payroll_contributions_icbf", "icbf >= 0"),
    ("ck_payroll_contributions_sena", "sena >= 0"),
    ("ck_payroll_contributions_severance", "severance >= 0"),
    ("ck_payroll_contributions_severance_interest", "severance_interest >= 0"),
    ("ck_payroll_contributions_vacation", "vacation >= 0"),
    ("ck_payroll_contributions_bonus", "bonus >= 0"),
)


def upgrade() -> None:
    for _name, column in EMPLOYEE_COLUMNS:
        op.add_column("employees", column)
    for _name, column in PERIOD_COLUMNS:
        op.add_column("payroll_periods", column)
    op.create_index("ix_payroll_periods_dian_status", "payroll_periods", ["dian_status"])

    op.create_table(
        "payroll_contributions",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("payroll_detail_id", sa.Uuid(), nullable=False),
        sa.Column("period_id", sa.Uuid(), nullable=False),
        *[column for _name, column in CONTRIBUTION_COLUMNS],
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_payroll_contributions"),
        sa.ForeignKeyConstraint(
            ["payroll_detail_id"],
            ["payroll_details.id"],
            name="fk_payroll_contributions_detail_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["period_id"],
            ["payroll_periods.id"],
            name="fk_payroll_contributions_period_id",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint("payroll_detail_id", name="uq_payroll_contributions_detail_id"),
        *[sa.CheckConstraint(expr, name=name) for name, expr in CONTRIBUTION_CHECKS],
    )
    op.create_index(
        "ix_payroll_contributions_period_id",
        "payroll_contributions",
        ["period_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_payroll_contributions_period_id", table_name="payroll_contributions")
    op.drop_table("payroll_contributions")

    op.drop_index("ix_payroll_periods_dian_status", table_name="payroll_periods")
    for name, _column in reversed(PERIOD_COLUMNS):
        op.drop_column("payroll_periods", name)
    for name, _column in reversed(EMPLOYEE_COLUMNS):
        op.drop_column("employees", name)
