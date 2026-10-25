"""Servicio de activos fijos con depreciación por línea recta.

La cuota mensual se calcula sobre la base depreciable
``initial_cost - salvage_value`` dividida entre ``useful_life_months``. En el
último mes se ajusta al saldo pendiente para no depreciar por encima del valor
de salvamento.

El servicio no hace commit. La API usa ``operation_transaction`` para que la
cuota y su asiento contable se confirmen o reviertan juntos.
"""

from __future__ import annotations

import calendar
from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy.orm import Session

from app.application.accounting.service import AccountingService
from app.domain.calculations import round_money
from app.domain.exceptions import (
    FixedAssetError,
    FixedAssetValidationError,
    ResourceNotFoundError,
)
from app.domain.fixed_asset_repository import FixedAssetRepository
from app.domain.models.fixed_asset import FixedAsset, FixedAssetStatus

ZERO = Decimal("0.00")


def _month_bounds(year: int, month: int) -> tuple[date, date]:
    """Devuelve el primer y último día del mes indicado."""
    last_day = calendar.monthrange(year, month)[1]
    return date(year, month, 1), date(year, month, last_day)


class FixedAssetService:
    """Lógica de negocio de activos fijos y depreciación."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.assets = FixedAssetRepository(db)
        self.accounting = AccountingService(db)

    def create_asset(
        self,
        *,
        code: str,
        name: str,
        purchase_date: date,
        initial_cost: Decimal,
        salvage_value: Decimal,
        useful_life_months: int,
    ) -> FixedAsset:
        """Registra un activo fijo validando su código único y su base depreciable."""
        normalized_code = code.strip()
        normalized_name = name.strip()

        if not normalized_code:
            raise FixedAssetValidationError("El código del activo es obligatorio")
        if not normalized_name:
            raise FixedAssetValidationError("El nombre del activo es obligatorio")

        initial_cost = round_money(initial_cost)
        salvage_value = round_money(salvage_value)
        if initial_cost <= ZERO:
            raise FixedAssetValidationError("El costo inicial debe ser mayor que cero")
        if salvage_value < ZERO:
            raise FixedAssetValidationError("El valor de salvamento no puede ser negativo")
        if salvage_value >= initial_cost:
            raise FixedAssetValidationError(
                "El valor de salvamento debe ser menor que el costo inicial"
            )
        if useful_life_months <= 0:
            raise FixedAssetValidationError("La vida útil debe ser mayor que cero")

        if self.assets.get_by_code(normalized_code) is not None:
            raise FixedAssetError(
                f"Ya existe un activo fijo con el código {normalized_code}"
            )

        asset = self.assets.create(
            {
                "code": normalized_code,
                "name": normalized_name,
                "purchase_date": purchase_date,
                "initial_cost": initial_cost,
                "salvage_value": salvage_value,
                "useful_life_months": useful_life_months,
                "status": FixedAssetStatus.ACTIVE,
            }
        )
        self.db.flush()
        return asset

    def depreciate_asset(
        self,
        *,
        asset_id: UUID,
        year: int,
        month: int,
    ) -> FixedAsset:
        """Registra la cuota mensual y su asiento contable.

        Reglas:
        - Solo activos ``ACTIVE``.
        - Una sola cuota por activo y mes calendario.
        - La fecha contable es el último día del mes depreciado.
        - La última cuota se limita al saldo pendiente para respetar el valor
          de salvamento.
        """
        asset = self.assets.get_by_id(asset_id)
        if asset is None:
            raise ResourceNotFoundError("Activo fijo no encontrado")

        if asset.status != FixedAssetStatus.ACTIVE:
            raise FixedAssetError(
                "Solo se pueden depreciar activos fijos en estado ACTIVE"
            )

        start_date, end_date = _month_bounds(year, month)
        if asset.purchase_date > end_date:
            raise FixedAssetValidationError(
                "El activo no puede depreciarse antes de su fecha de compra"
            )

        existing = self.assets.get_depreciation_between(
            asset_id=asset.id,
            start_date=start_date,
            end_date=end_date,
        )
        if existing is not None:
            raise FixedAssetError(
                f"El activo ya fue depreciado para el periodo {month:02d}/{year}"
            )

        base = round_money(asset.initial_cost - asset.salvage_value)
        monthly_amount = round_money(base / Decimal(asset.useful_life_months))
        remaining = round_money(base - asset.accumulated_depreciation)

        if remaining <= ZERO:
            raise FixedAssetError("El activo ya está totalmente depreciado")
        if monthly_amount <= ZERO:
            raise FixedAssetValidationError(
                "La cuota mensual resulta cero; revisa la vida útil y el costo"
            )

        amount = min(monthly_amount, remaining)
        depreciation = self.assets.create_depreciation(
            asset=asset,
            date=end_date,
            amount=amount,
        )

        entry = self.accounting.record_depreciation(depreciation)
        depreciation.accounting_entry_id = entry.id
        self.db.flush()
        return asset


__all__ = ["FixedAssetService"]
