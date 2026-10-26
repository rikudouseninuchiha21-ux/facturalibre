"""Datos DIAN para el generador XML UBL 2.1 y PDF (Fase 38A).

Revision ID: 20261026_0026
Revises: 20261025_0025
Create Date: 2026-10-26

Agrega las columnas/catálogos que el Anexo Técnico de Factura Electrónica
v1.9 exige para armar un XML UBL 2.1 estructuralmente válido y el PDF de
representación gráfica (Resolución 000165/2023). Todo es NULL-able o con
default para no romper históricos; el NIT de la empresa ya vivía en
``company_settings.tax_id``.

Decisiones documentadas:
- ``dian_status`` es un ENUM nativo (``dian_document_status``) con la
  variante extra ``GENERADO_SIN_PIN``, siguiendo la regla de oro de estados
  del proyecto (StrEnum → enum PG) en lugar del VARCHAR del borrador.
- ``contacts.address`` y ``items.unit_code`` se agregan además de lo listado:
  el XML requiere dirección física del adquiriente y ``unitCode`` en
  ``cbc:InvoicedQuantity``. Sin ellas el XML no puede ser válido.
- No se firma XAdES ni se envía a la DIAN en esta fase.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "20261026_0026"
down_revision: str | None = "20261025_0025"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

dian_status_enum = postgresql.ENUM(
    "BORRADOR",
    "GENERADO",
    "GENERADO_SIN_PIN",
    "ENVIADO",
    "ACEPTADO",
    "RECHAZADO",
    name="dian_document_status",
    create_type=False,
)


def _add_columns(table: str, columns: tuple[sa.Column, ...]) -> None:
    for column in columns:
        op.add_column(table, column)


def _drop_columns(table: str, names: tuple[str, ...]) -> None:
    for name in names:
        op.drop_column(table, name)


def upgrade() -> None:
    bind = op.get_bind()
    dian_status_enum.create(bind, checkfirst=True)

    _add_columns(
        "invoices",
        (
            sa.Column("cufe", sa.String(96), nullable=True),
            sa.Column("dian_status", dian_status_enum, nullable=True),
            sa.Column("xml_generated_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("payment_mean_code", sa.String(2), nullable=True),
            sa.Column("payment_terms_days", sa.Integer(), nullable=True),
            sa.Column("notes_dian", sa.Text(), nullable=True),
            sa.Column("order_reference", sa.String(30), nullable=True),
        ),
    )
    op.create_index("ix_invoices_dian_status", "invoices", ["dian_status"])

    _add_columns(
        "contacts",
        (
            sa.Column("dv", sa.String(2), nullable=True),
            sa.Column("tax_regime", sa.String(20), nullable=True),
            sa.Column("person_type", sa.String(20), nullable=True),
            sa.Column("fiscal_responsibility", sa.String(50), nullable=True),
            sa.Column("dian_municipality_code", sa.String(5), nullable=True),
            sa.Column("dian_department_code", sa.String(2), nullable=True),
            sa.Column(
                "country_code",
                sa.String(3),
                nullable=False,
                server_default=sa.text("'CO'"),
            ),
            sa.Column("address", sa.String(300), nullable=True),
        ),
    )

    _add_columns(
        "company_settings",
        (
            sa.Column("dv", sa.String(2), nullable=True),
            sa.Column("tax_regime", sa.String(20), nullable=True),
            sa.Column("person_type", sa.String(20), nullable=True),
            sa.Column("fiscal_responsibility", sa.String(50), nullable=True),
            sa.Column("dian_municipality_code", sa.String(5), nullable=True),
            sa.Column("dian_department_code", sa.String(2), nullable=True),
            sa.Column(
                "country_code",
                sa.String(3),
                nullable=False,
                server_default=sa.text("'CO'"),
            ),
            sa.Column("dian_resolution_number", sa.String(20), nullable=True),
            sa.Column("dian_resolution_prefix", sa.String(4), nullable=True),
            sa.Column("dian_resolution_range_from", sa.BigInteger(), nullable=True),
            sa.Column("dian_resolution_range_to", sa.BigInteger(), nullable=True),
            sa.Column("dian_resolution_valid_from", sa.Date(), nullable=True),
            sa.Column("dian_resolution_valid_to", sa.Date(), nullable=True),
            sa.Column("dian_software_id", sa.String(100), nullable=True),
            sa.Column("dian_software_pin", sa.String(100), nullable=True),
            sa.Column(
                "dian_environment",
                sa.String(20),
                nullable=False,
                server_default=sa.text("'HABILITACION'"),
            ),
        ),
    )

    _add_columns(
        "items",
        (
            sa.Column("dian_code", sa.String(50), nullable=True),
            sa.Column("unspsc_code", sa.String(10), nullable=True),
            sa.Column(
                "unit_code",
                sa.String(10),
                nullable=True,
                server_default=sa.text("'UND'"),
            ),
        ),
    )

    _add_columns(
        "taxes",
        (
            sa.Column("dian_tax_code", sa.String(2), nullable=True),
            sa.Column("dian_tax_name", sa.String(50), nullable=True),
        ),
    )


def downgrade() -> None:
    _drop_columns(
        "taxes",
        ("dian_tax_code", "dian_tax_name"),
    )

    _drop_columns(
        "items",
        ("dian_code", "unspsc_code", "unit_code"),
    )

    _drop_columns(
        "company_settings",
        (
            "dv",
            "tax_regime",
            "person_type",
            "fiscal_responsibility",
            "dian_municipality_code",
            "dian_department_code",
            "country_code",
            "dian_resolution_number",
            "dian_resolution_prefix",
            "dian_resolution_range_from",
            "dian_resolution_range_to",
            "dian_resolution_valid_from",
            "dian_resolution_valid_to",
            "dian_software_id",
            "dian_software_pin",
            "dian_environment",
        ),
    )

    _drop_columns(
        "contacts",
        (
            "dv",
            "tax_regime",
            "person_type",
            "fiscal_responsibility",
            "dian_municipality_code",
            "dian_department_code",
            "country_code",
            "address",
        ),
    )

    op.drop_index("ix_invoices_dian_status", table_name="invoices")
    _drop_columns(
        "invoices",
        (
            "cufe",
            "dian_status",
            "xml_generated_at",
            "payment_mean_code",
            "payment_terms_days",
            "notes_dian",
            "order_reference",
        ),
    )

    dian_status_enum.drop(bind=op.get_bind(), checkfirst=True)
