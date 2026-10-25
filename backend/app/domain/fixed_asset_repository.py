"""Acceso a datos de activos fijos y sus cuotas de depreciación."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.domain.models.fixed_asset import DepreciationEntry, FixedAsset


class FixedAssetRepository:
    """Consultas y persistencia de activos fijos.

    El repositorio no confirma transacciones: la API envuelve la creación de la
    cuota y su asiento contable con ``operation_transaction``.
    """

    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, values: dict[str, Any]) -> FixedAsset:
        """Crea un activo fijo y lo persiste sin confirmar la transacción."""
        asset = FixedAsset(**values)
        self.db.add(asset)
        self.db.flush()
        self.db.refresh(asset)
        return asset

    def get_by_id(self, asset_id: UUID) -> FixedAsset | None:
        """Obtiene un activo con sus cuotas de depreciación cargadas."""
        statement = (
            select(FixedAsset)
            .where(FixedAsset.id == asset_id)
            .options(selectinload(FixedAsset.depreciation_entries))
        )
        return self.db.scalar(statement)

    def get_by_code(self, code: str) -> FixedAsset | None:
        """Busca un activo por su código único."""
        statement = select(FixedAsset).where(FixedAsset.code == code)
        return self.db.scalar(statement)

    def list(self, *, limit: int, offset: int) -> list[FixedAsset]:
        """Lista activos con sus cuotas para calcular depreciación acumulada."""
        statement = (
            select(FixedAsset)
            .options(selectinload(FixedAsset.depreciation_entries))
            .order_by(FixedAsset.code, FixedAsset.id)
            .limit(limit)
            .offset(offset)
        )
        return list(self.db.scalars(statement).all())

    def get_depreciation_between(
        self,
        *,
        asset_id: UUID,
        start_date: date,
        end_date: date,
    ) -> DepreciationEntry | None:
        """Busca una cuota del activo dentro del rango de un mes calendario."""
        statement = select(DepreciationEntry).where(
            DepreciationEntry.asset_id == asset_id,
            DepreciationEntry.date >= start_date,
            DepreciationEntry.date <= end_date,
        )
        return self.db.scalar(statement)

    def create_depreciation(
        self,
        *,
        asset: FixedAsset,
        date: date,
        amount: Decimal,
    ) -> DepreciationEntry:
        """Crea una cuota mensual y la asocia al activo en memoria.

        La asociación por relación mantiene actualizada la lista
        ``asset.depreciation_entries`` cuando ya estaba cargada, de modo que la
        respuesta puede reflejar la nueva depreciación sin una recarga extra.
        """
        depreciation = DepreciationEntry(asset=asset, date=date, amount=amount)
        self.db.add(depreciation)
        self.db.flush()
        return depreciation


__all__ = ["FixedAssetRepository"]
