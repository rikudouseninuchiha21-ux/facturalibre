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


class ContactType(enum.StrEnum):
    CUSTOMER = "customer"
    SUPPLIER = "supplier"
    BOTH = "both"


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
    # -- REQUIERE VALIDACIÓN: contador/experto DIAN (formato de identificación fiscal).
    tax_id: Mapped[str | None] = mapped_column(
        String(30),
        comment=(
            "REQUIERE VALIDACIÓN: contador/experto DIAN. "
            "Formato y validación de identificación fiscal."
        ),
    )

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
