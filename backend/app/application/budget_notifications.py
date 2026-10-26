"""Disparador de notificaciones por cruce de umbral presupuestal.

Detección del "cruce" (decisión documentada): el nivel de alerta NO se
persiste; es derivado de la contabilidad. Se comparan los niveles derivados
ANTES y DESPUÉS del asiento que cambia el gasto real, dentro de la MISMA
transacción de la operación de negocio:

1. ``capture_alert_levels`` se llama antes de generar el asiento y devuelve
   ``{budget_id: nivel}`` de los presupuestos APPROVED del centro y mes.
2. ``notify_threshold_crossings`` se llama después del asiento: recalcula y
   notifica solo cuando el nivel CAMBIA y queda en WARNING/CRITICAL/OVER.

Así no hay spam (recalcular sin cambio de nivel no notifica), no se persiste
nada derivado y la atomicidad es la de la transacción original: si la
operación falla, tampoco quedan notificaciones huérfanas.
"""

from __future__ import annotations

from datetime import date
from uuid import UUID

from sqlalchemy.orm import Session

from app.application.budget_actuals_service import BudgetActualsService
from app.application.budget_alerts import ALERTING_LEVELS, BudgetAlertLevel
from app.application.notification_service import NotificationService
from app.domain.budget_repository import BudgetRepository
from app.domain.models.auth import UserRole
from app.domain.models.budgeting import Budget, BudgetStatus
from app.domain.models.notification import NotificationSeverity


def _approved_budgets(
    db: Session,
    *,
    cost_center_id: UUID,
    entry_date: date,
) -> list[Budget]:
    return BudgetRepository(db).list(
        cost_center_id=cost_center_id,
        period_year=entry_date.year,
        period_month=entry_date.month,
        status=BudgetStatus.APPROVED,
    )


def capture_alert_levels(
    db: Session,
    *,
    cost_center_id: UUID,
    entry_date: date,
) -> dict[UUID, BudgetAlertLevel]:
    """Niveles de alerta de los presupuestos APPROVED antes del asiento."""
    actuals = BudgetActualsService(db)
    return {
        budget.id: actuals.totals_for(budget).alert_level_total
        for budget in _approved_budgets(db, cost_center_id=cost_center_id, entry_date=entry_date)
    }


def notify_threshold_crossings(
    db: Session,
    *,
    previous: dict[UUID, BudgetAlertLevel],
    cost_center_id: UUID,
    entry_date: date,
) -> int:
    """Notifica los presupuestos cuyo nivel de alerta subió por el asiento.

    Solo se notifica cuando el nivel cambia y queda en WARNING/CRITICAL/OVER;
    recalcular el mismo nivel nunca genera notificaciones duplicadas.
    Retorna cuántas notificaciones se crearon (una por usuario destino).
    """
    actuals = BudgetActualsService(db)
    notifier = NotificationService(db)
    created = 0
    for budget in _approved_budgets(db, cost_center_id=cost_center_id, entry_date=entry_date):
        totals = actuals.totals_for(budget)
        after = totals.alert_level_total
        before = previous.get(budget.id)
        if after == before or after not in ALERTING_LEVELS:
            continue

        severity = (
            NotificationSeverity.CRITICAL
            if after in ("CRITICAL", "OVER")
            else NotificationSeverity.WARNING
        )
        utilization = (
            "sin base presupuestada"
            if totals.utilization_pct_total is None
            else f"{totals.utilization_pct_total}%"
        )
        created += notifier.create_for_roles(
            roles=[UserRole.ADMIN, UserRole.ACCOUNTANT],
            category="BUDGET_ALERT",
            severity=severity,
            title=f"Presupuesto en nivel {after}: {budget.cost_center.name}",
            body=(
                f"La utilización del presupuesto de {budget.cost_center.name} "
                f"para {budget.period_month:02d}/{budget.period_year} llegó a "
                f"{utilization} (${totals.actual} de ${totals.budgeted})."
            ),
            link=f"/budgets/{budget.id}",
        )
    return created


__all__ = ["capture_alert_levels", "notify_threshold_crossings"]
