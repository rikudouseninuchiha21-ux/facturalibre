"""Multi-empresa: companies, membresías y aislamiento por company_id.

Revision ID: 20261028_0029
Revises: 20261027_0028
Create Date: 2026-10-28

Crea el tenant ``companies``, la tabla puente ``user_companies`` y agrega
``company_id`` a todas las tablas de negocio. Los datos históricos se asignan
a la empresa existente en ``company_settings`` (o a una empresa por defecto si
todavía no hay configuración).
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "20261028_0029"
down_revision: str | None = "20261027_0028"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

DEFAULT_COMPANY_ID = "00000000-0000-0000-0000-000000000001"

SCOPED_TABLES: tuple[str, ...] = (
    "accounting_entries",
    "accounting_entry_lines",
    "bank_accounts",
    "bank_transactions",
    "budget_lines",
    "budgets",
    "company_settings",
    "contacts",
    "cost_centers",
    "credit_note_lines",
    "credit_notes",
    "depreciation_entries",
    "employees",
    "expenses",
    "fiscal_periods",
    "fixed_assets",
    "idempotency_keys",
    "invoice_lines",
    "invoices",
    "items",
    "notifications",
    "number_sequences",
    "payment_agreement_installments",
    "payment_agreements",
    "payment_reminders",
    "payments",
    "payroll_contributions",
    "payroll_details",
    "payroll_periods",
    "purchase_invoices",
    "purchase_lines",
    "purchase_payments",
    "quote_lines",
    "quotes",
    "stock_balances",
    "stock_movements",
    "taxes",
    "warehouses",
)

# (tabla, restricción antigua, restricción nueva, columnas nuevas)
UNIQUE_CHANGES: tuple[tuple[str, str, str, tuple[str, ...]], ...] = (
    ("invoices", "uq_invoices_number", "uq_invoices_company_number", ("company_id", "number")),
    ("quotes", "uq_quotes_number", "uq_quotes_company_number", ("company_id", "number")),
    (
        "warehouses",
        "uq_warehouses_code",
        "uq_warehouses_company_code",
        ("company_id", "code"),
    ),
    (
        "employees",
        "uq_employees_document",
        "uq_employees_company_document",
        ("company_id", "document"),
    ),
    (
        "number_sequences",
        "uq_number_sequences_name",
        "uq_number_sequences_company_name",
        ("company_id", "name"),
    ),
    (
        "idempotency_keys",
        "uq_idempotency_keys_key",
        "uq_idempotency_keys_company_key",
        ("company_id", "key"),
    ),
    (
        "cost_centers",
        "uq_cost_centers_code",
        "uq_cost_centers_company_code",
        ("company_id", "code"),
    ),
    (
        "fixed_assets",
        "uq_fixed_assets_code",
        "uq_fixed_assets_company_code",
        ("company_id", "code"),
    ),
    (
        "fiscal_periods",
        "uq_fiscal_periods_month_year",
        "uq_fiscal_periods_company_month_year",
        ("company_id", "month", "year"),
    ),
    (
        "payroll_periods",
        "uq_payroll_periods_month_year",
        "uq_payroll_periods_company_month_year",
        ("company_id", "month", "year"),
    ),
    (
        "budgets",
        "uq_budgets_cost_center_period",
        "uq_budgets_company_cost_center_period",
        ("company_id", "cost_center_id", "period_year", "period_month"),
    ),
    (
        "bank_accounts",
        "uq_bank_accounts_bank_name_account_number",
        "uq_bank_accounts_company_bank_account",
        ("company_id", "bank_name", "account_number"),
    ),
    (
        "accounting_entries",
        "uq_accounting_entries_source_type_source_id",
        "uq_accounting_entries_company_source",
        ("company_id", "source_type", "source_id"),
    ),
)


def _default_company_id(bind: sa.Connection) -> tuple[str, bool]:
    """Crea la empresa inicial y devuelve ``(id, settings_exist)``."""
    row = (
        bind.execute(
            sa.text(
                "SELECT id, name, tax_id, dv, address, phone, email, tax_regime, "
                "person_type, fiscal_responsibility, dian_municipality_code, "
                "dian_department_code "
                "FROM company_settings ORDER BY created_at, id LIMIT 1"
            )
        )
        .mappings()
        .first()
    )

    if row is None:
        bind.execute(
            sa.text("INSERT INTO companies (id, name) VALUES (:id, :name)"),
            {"id": DEFAULT_COMPANY_ID, "name": "Mi Empresa S.A.S."},
        )
        return DEFAULT_COMPANY_ID, False

    company_id = str(row["id"])
    bind.execute(
        sa.text(
            "INSERT INTO companies ("
            "id, name, tax_id, dv, address, phone, email, tax_regime, person_type, "
            "fiscal_responsibility, dian_municipality_code, dian_department_code"
            ") VALUES ("
            ":id, :name, :tax_id, :dv, :address, :phone, :email, :tax_regime, "
            ":person_type, :fiscal_responsibility, :dian_municipality_code, "
            ":dian_department_code"
            ")"
        ),
        {
            "id": company_id,
            "name": row["name"],
            "tax_id": row["tax_id"],
            "dv": row["dv"],
            "address": row["address"],
            "phone": row["phone"],
            "email": row["email"],
            "tax_regime": row["tax_regime"],
            "person_type": row["person_type"],
            "fiscal_responsibility": row["fiscal_responsibility"],
            "dian_municipality_code": row["dian_municipality_code"],
            "dian_department_code": row["dian_department_code"],
        },
    )
    return company_id, True


def upgrade() -> None:
    op.create_table(
        "companies",
        sa.Column(
            "id",
            sa.Uuid(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("tax_id", sa.String(length=30), nullable=True),
        sa.Column("dv", sa.String(length=2), nullable=True),
        sa.Column("address", sa.String(length=300), nullable=True),
        sa.Column("phone", sa.String(length=30), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("tax_regime", sa.String(length=20), nullable=True),
        sa.Column("person_type", sa.String(length=20), nullable=True),
        sa.Column("fiscal_responsibility", sa.String(length=50), nullable=True),
        sa.Column("dian_municipality_code", sa.String(length=5), nullable=True),
        sa.Column("dian_department_code", sa.String(length=2), nullable=True),
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
        sa.PrimaryKeyConstraint("id", name="pk_companies"),
        sa.UniqueConstraint("tax_id", name="uq_companies_tax_id"),
    )

    op.create_table(
        "user_companies",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("company_id", sa.Uuid(), nullable=False),
        sa.Column(
            "role",
            postgresql.ENUM(name="user_role", create_type=False),
            server_default=sa.text("'ADMIN'"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_user_companies_user_id_users",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["company_id"],
            ["companies.id"],
            name="fk_user_companies_company_id_companies",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("user_id", "company_id", name="pk_user_companies"),
    )

    op.add_column("sessions", sa.Column("active_company_id", sa.Uuid(), nullable=True))
    op.create_index(
        "ix_sessions_active_company_id", "sessions", ["active_company_id"], unique=False
    )
    op.create_foreign_key(
        "fk_sessions_active_company_id_companies",
        "sessions",
        "companies",
        ["active_company_id"],
        ["id"],
        ondelete="SET NULL",
    )

    bind = op.get_bind()
    default_company_id, settings_exist = _default_company_id(bind)

    # El DEFAULT de la columna rellena las filas históricas en el mismo DDL,
    # sin UPDATE masivos que dejen eventos de trigger pendientes para el
    # ALTER TABLE posterior. Después se retira el DEFAULT para que ninguna
    # inserción futura caiga silenciosamente en la empresa histórica.
    for table in SCOPED_TABLES:
        op.add_column(
            table,
            sa.Column(
                "company_id",
                sa.Uuid(),
                nullable=False,
                server_default=sa.text(f"'{default_company_id}'"),
            ),
        )
        op.alter_column(table, "company_id", server_default=None)

    for table in SCOPED_TABLES:
        op.create_index(f"ix_{table}_company_id", table, ["company_id"], unique=False)
        op.create_foreign_key(
            f"fk_{table}_company_id_companies",
            table,
            "companies",
            ["company_id"],
            ["id"],
            ondelete="RESTRICT",
        )

    op.create_unique_constraint(
        "uq_company_settings_company_id", "company_settings", ["company_id"]
    )

    for table, old_name, new_name, columns in UNIQUE_CHANGES:
        op.drop_constraint(old_name, table, type_="unique")
        op.create_unique_constraint(new_name, table, list(columns))

    if not settings_exist:
        bind.execute(
            sa.text("INSERT INTO company_settings (company_id, name) VALUES (:company_id, :name)"),
            {"company_id": default_company_id, "name": "Mi Empresa S.A.S."},
        )

    # Membresías iniciales: todos los usuarios existentes acceden a la empresa
    # histórica con su rol global.
    bind.execute(
        sa.text(
            "INSERT INTO user_companies (user_id, company_id, role) "
            "SELECT id, :company_id, role FROM users ON CONFLICT DO NOTHING"
        ),
        {"company_id": default_company_id},
    )
    bind.execute(
        sa.text("UPDATE sessions SET active_company_id = :company_id"),
        {"company_id": default_company_id},
    )


def downgrade() -> None:
    for table, old_name, new_name, _columns in reversed(UNIQUE_CHANGES):
        op.drop_constraint(new_name, table, type_="unique")
        op.create_unique_constraint(old_name, table, _columns[1:])

    op.drop_constraint("uq_company_settings_company_id", "company_settings", type_="unique")

    for table in reversed(SCOPED_TABLES):
        op.drop_constraint(f"fk_{table}_company_id_companies", table, type_="foreignkey")
        op.drop_index(f"ix_{table}_company_id", table_name=table)
        op.drop_column(table, "company_id")

    op.drop_constraint("fk_sessions_active_company_id_companies", "sessions", type_="foreignkey")
    op.drop_index("ix_sessions_active_company_id", table_name="sessions")
    op.drop_column("sessions", "active_company_id")

    op.drop_table("user_companies")
    op.drop_table("companies")
