"""Lógica de negocio de presupuestos mensuales por centro de costo.

Reglas de estado:
- Solo los presupuestos DRAFT se pueden editar (cabecera y líneas) o borrar.
- ``approve`` exige al menos una línea y un total mayor que cero.
- ``close`` solo se permite sobre un presupuesto APPROVED.

El servicio no hace commit. La API controla la transacción vía
``operation_transaction``.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.application.notification_service import NotificationService
from app.domain.accounting_repository import AccountingRepository
from app.domain.budget_repository import BudgetRepository
from app.domain.cost_center_repository import CostCenterRepository
from app.domain.exceptions import (
    BudgetStateError,
    BudgetValidationError,
    ResourceNotFoundError,
)
from app.domain.models.auth import UserRole
from app.domain.models.budgeting import Budget, BudgetLine, BudgetStatus
from app.domain.models.notification import NotificationSeverity

ZERO = Decimal("0.00")


class BudgetService:
    """CRUD de presupuestos con ciclo de vida DRAFT → APPROVED → CLOSED."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.budgets = BudgetRepository(db)
        self.cost_centers = CostCenterRepository(db)
        self.accounts = AccountingRepository(db)

    # -- Cabecera ---------------------------------------------------------

    def create(
        self,
        *,
        cost_center_id: UUID,
        period_year: int,
        period_month: int,
        name: str | None = None,
        notes: str | None = None,
    ) -> Budget:
        """Abre un presupuesto DRAFT; un centro no puede tener dos presupuestos del mismo mes."""
        if self.cost_centers.get_by_id(cost_center_id) is None:
            raise ResourceNotFoundError("Centro de costo no encontrado")
        existing = self.budgets.find_by_period(
            cost_center_id=cost_center_id,
            period_year=period_year,
            period_month=period_month,
        )
        if existing is not None:
            raise BudgetValidationError(
                "El centro de costo ya tiene un presupuesto para ese periodo"
            )
        return self.budgets.create(
            {
                "cost_center_id": cost_center_id,
                "period_year": period_year,
                "period_month": period_month,
                "name": name,
                "notes": notes,
                "status": BudgetStatus.DRAFT,
            }
        )

    def get(self, budget_id: UUID) -> Budget:
        budget = self.budgets.get_by_id(budget_id)
        if budget is None:
            raise ResourceNotFoundError("Presupuesto no encontrado")
        return budget

    def list(
        self,
        *,
        cost_center_id: UUID | None = None,
        period_year: int | None = None,
        period_month: int | None = None,
        status: BudgetStatus | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Budget]:
        return self.budgets.list(
            cost_center_id=cost_center_id,
            period_year=period_year,
            period_month=period_month,
            status=status,
            limit=limit,
            offset=offset,
        )

    def update(self, budget_id: UUID, values: dict[str, Any]) -> Budget:
        """Actualiza la cabecera; solo permitido en DRAFT."""
        budget = self.get(budget_id)
        self._require_draft(budget)
        return self.budgets.update(budget, values)

    def delete(self, budget_id: UUID) -> None:
        """Elimina el presupuesto con sus líneas; solo permitido en DRAFT."""
        budget = self.get(budget_id)
        self._require_draft(budget)
        self.budgets.delete(budget)

    # -- Líneas -----------------------------------------------------------

    def add_line(
        self,
        budget_id: UUID,
        *,
        account_code: str,
        amount: Decimal,
        notes: str | None = None,
    ) -> BudgetLine:
        """Agrega una cuenta PUC presupuestada; solo en DRAFT."""
        budget = self.get(budget_id)
        self._require_draft(budget)

        if self.accounts.get_account_by_code(account_code) is None:
            raise BudgetValidationError(f"Cuenta PUC no encontrada: {account_code}")
        if self.budgets.line_exists(budget.id, account_code):
            raise BudgetValidationError(
                f"La cuenta {account_code} ya está presupuestada en este presupuesto"
            )
        return self.budgets.add_line(
            budget,
            account_code=account_code,
            amount=amount,
            notes=notes,
        )

    def update_line(
        self,
        budget_id: UUID,
        line_id: UUID,
        values: dict[str, Any],
    ) -> BudgetLine:
        budget = self.get(budget_id)
        self._require_draft(budget)
        line = self.budgets.get_line(budget.id, line_id)
        if line is None:
            raise ResourceNotFoundError("Línea de presupuesto no encontrada")
        return self.budgets.update_line(line, values)

    def remove_line(self, budget_id: UUID, line_id: UUID) -> None:
        budget = self.get(budget_id)
        self._require_draft(budget)
        line = self.budgets.get_line(budget.id, line_id)
        if line is None:
            raise ResourceNotFoundError("Línea de presupuesto no encontrada")
        self.budgets.remove_line(line)

    # -- Ciclo de vida ------------------------------------------------------

    def approve(self, budget_id: UUID) -> Budget:
        """DRAFT → APPROVED; exige al menos una línea y total > 0."""
        budget = self.get(budget_id)
        if budget.status is not BudgetStatus.DRAFT:
            raise BudgetStateError("Solo se pueden aprobar presupuestos en borrador")
        if not budget.lines:
            raise BudgetValidationError(
                "El presupuesto debe tener al menos una línea para aprobarse"
            )
        total = sum((line.amount for line in budget.lines), ZERO)
        if total <= ZERO:
            raise BudgetValidationError(
                "El presupuesto debe tener un total mayor que cero para aprobarse"
            )
        approved = self.budgets.update(budget, {"status": BudgetStatus.APPROVED})

        # Notificación in-app dentro de la misma transacción: si la aprobación
        # falla, tampoco queda notificación huérfana.
        NotificationService(self.db).create_for_roles(
            roles=[UserRole.ADMIN, UserRole.ACCOUNTANT],
            category="BUDGET_APPROVED",
            severity=NotificationSeverity.INFO,
            title=f"Presupuesto aprobado: {approved.cost_center.name}",
            body=(
                f"El presupuesto de {approved.cost_center.name} para "
                f"{approved.period_month:02d}/{approved.period_year} fue "
                f"aprobado por un total de ${total}."
            ),
            link=f"/budgets/{approved.id}",
        )
        return approved

    def close(self, budget_id: UUID) -> Budget:
        """APPROVED → CLOSED; el presupuesto queda inmutable."""
        budget = self.get(budget_id)
        if budget.status is not BudgetStatus.APPROVED:
            raise BudgetStateError("Solo se pueden cerrar presupuestos aprobados")
        return self.budgets.update(budget, {"status": BudgetStatus.CLOSED})

    def close_by_period(self, *, period_year: int, period_month: int) -> int:
        """Cierra automáticamente los presupuestos APPROVED de un periodo.

        Se invoca dentro del cierre del periodo fiscal contable, en la MISMA
        transacción, de modo que el periodo y los presupuestos se confirman o
        revierten juntos. Solo cierra presupuestos APPROVED: los DRAFT quedan
        intactos porque quien no aprobó no tiene compromiso real de gasto.

        Idempotente: si no hay presupuestos APPROVED retorna 0 sin error.
        No abre transacciones nuevas; reutiliza la sesión existente.

        La reapertura del periodo fiscal NO reabre presupuestos: debe ser
        manual por un ADMIN con auditoría, porque reabrir el control
        presupuestal de un mes cerrado es una decisión de negocio.
        """
        budgets = self.budgets.list(
            period_year=period_year,
            period_month=period_month,
            status=BudgetStatus.APPROVED,
        )
        notifier = NotificationService(self.db)
        for budget in budgets:
            budget.status = BudgetStatus.CLOSED
        self.db.flush()

        # Notificación in-app por presupuesto cerrado, en la misma transacción
        # del cierre del periodo fiscal (o de la llamada directa).
        for budget in budgets:
            notifier.create_for_roles(
                roles=[UserRole.ADMIN],
                category="BUDGET_CLOSED",
                severity=NotificationSeverity.INFO,
                title=f"Presupuesto cerrado: {budget.cost_center.name}",
                body=(
                    f"El presupuesto de {budget.cost_center.name} de "
                    f"{budget.period_month:02d}/{budget.period_year} pasó a "
                    "CLOSED por el cierre del periodo contable."
                ),
                link=f"/budgets/{budget.id}",
            )
        return len(budgets)

    def _require_draft(self, budget: Budget) -> None:
        if budget.status is not BudgetStatus.DRAFT:
            raise BudgetStateError("El presupuesto no se puede editar porque no está en borrador")


__all__ = ["BudgetService"]
