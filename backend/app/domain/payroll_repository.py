"""Acceso a datos de periodos y detalles de nómina."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.domain.models.payroll import PayrollDetail, PayrollPeriod


class PayrollRepository:
    """Consultas y persistencia de la liquidación de nómina.

    No confirma la transacción del cálculo: el servicio y la API agrupan el
    detalle, el estado del periodo y el asiento contable en una sola operación.
    """

    def __init__(self, db: Session) -> None:
        self.db = db

    def create_period(self, values: dict[str, Any]) -> PayrollPeriod:
        """Crea un periodo en borrador y confirma la transacción."""
        period = PayrollPeriod(**values)
        self.db.add(period)
        self.db.commit()
        self.db.refresh(period)
        return period

    def get_by_id(self, period_id: UUID) -> PayrollPeriod | None:
        """Obtiene un periodo con su detalle y los empleados asociados."""
        statement = (
            select(PayrollPeriod)
            .where(PayrollPeriod.id == period_id)
            .options(selectinload(PayrollPeriod.details).selectinload(PayrollDetail.employee))
        )
        return self.db.scalar(statement)

    def get_for_update(self, period_id: UUID) -> PayrollPeriod | None:
        """Bloquea el periodo para evitar dos cálculos concurrentes."""
        statement = select(PayrollPeriod).where(PayrollPeriod.id == period_id).with_for_update()
        return self.db.scalar(statement)

    def list(self, *, limit: int, offset: int) -> list[PayrollPeriod]:
        """Lista periodos con su detalle, del más reciente al más antiguo."""
        statement = (
            select(PayrollPeriod)
            .options(selectinload(PayrollPeriod.details).selectinload(PayrollDetail.employee))
            .order_by(
                PayrollPeriod.year.desc(),
                PayrollPeriod.month.desc(),
                PayrollPeriod.id,
            )
            .limit(limit)
            .offset(offset)
        )
        return list(self.db.scalars(statement).all())

    def has_details(self, period_id: UUID) -> bool:
        """Indica si el periodo ya tiene detalle de liquidación."""
        return (
            self.db.scalar(
                select(PayrollDetail.id).where(PayrollDetail.period_id == period_id).limit(1)
            )
            is not None
        )

    def rollback(self) -> None:
        """Revierte la transacción en curso tras un error de integridad."""
        self.db.rollback()
