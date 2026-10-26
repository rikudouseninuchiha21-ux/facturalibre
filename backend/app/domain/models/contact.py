"""Modelo de contactos (clientes y proveedores)."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, Integer, String, Uuid, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.database import Base

if TYPE_CHECKING:
    from app.domain.models.invoice import Invoice
    from app.domain.models.purchase import PurchaseInvoice
    from app.domain.models.quote import Quote


class ContactType(enum.StrEnum):
    CUSTOMER = "customer"
    SUPPLIER = "supplier"
    BOTH = "both"


class ContactStatus(enum.StrEnum):
    LEAD = "LEAD"
    PROSPECT = "PROSPECT"
    CUSTOMER = "CUSTOMER"


def _enum_values(enum_cls: type[enum.StrEnum]) -> list[str]:
    """Persiste los valores, no los nombres, de los enums."""
    return [member.value for member in enum_cls]


class Contact(Base):
    __tablename__ = "contacts"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    email: Mapped[str | None] = mapped_column(String(255))
    type: Mapped[ContactType] = mapped_column(
        Enum(
            ContactType,
            name="contact_type",
            native_enum=True,
            values_callable=_enum_values,
        ),
        nullable=False,
        default=ContactType.CUSTOMER,
        server_default=text("'customer'"),
        index=True,
    )
    status: Mapped[ContactStatus] = mapped_column(
        Enum(
            ContactStatus,
            name="contact_status",
            native_enum=True,
            values_callable=_enum_values,
        ),
        nullable=False,
        default=ContactStatus.CUSTOMER,
        server_default=text("'CUSTOMER'"),
        index=True,
    )
    # -- REQUIERE VALIDACIÓN: contador/experto DIAN (formato de identificación fiscal).
    tax_id: Mapped[str | None] = mapped_column(
        String(30),
        comment=(
            "REQUIERE VALIDACIÓN: contador/experto DIAN. "
            "Formato y validación de identificación fiscal."
        ),
    )

    # -- Fase 38A: datos fiscales DIAN del adquiriente/proveedor.
    dv: Mapped[str | None] = mapped_column(String(2))
    tax_regime: Mapped[str | None] = mapped_column(String(20))
    person_type: Mapped[str | None] = mapped_column(String(20))
    fiscal_responsibility: Mapped[str | None] = mapped_column(String(50))
    dian_municipality_code: Mapped[str | None] = mapped_column(String(5))
    dian_department_code: Mapped[str | None] = mapped_column(String(2))
    country_code: Mapped[str] = mapped_column(
        String(3), nullable=False, server_default=text("'CO'")
    )
    # Dirección física para el XML/PDF DIAN (no existía en el catálogo).
    address: Mapped[str | None] = mapped_column(String(300))

    # DECISIONES.md: bloqueo optimista y soft delete en datos maestros.
    version: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1, server_default=text("1")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    invoices: Mapped[list[Invoice]] = relationship(back_populates="contact")
    purchase_invoices: Mapped[list[PurchaseInvoice]] = relationship(back_populates="supplier")
    quotes: Mapped[list[Quote]] = relationship(back_populates="contact")
