"""Umbrales de utilización presupuestal y niveles de alerta de sobregiro.

Único lugar del sistema donde viven los umbrales. El backend calcula el
nivel y lo expone al frontend, que nunca lo recalcula.

Niveles:
- OK       → utilización < 80%
- WARNING  → 80% <= utilización < 90%
- CRITICAL → 90% <= utilización < 100%
- OVER     → utilización >= 100% (sobregiro)
- N/A      → presupuesto en cero (sin base de cálculo)

La utilización es un valor derivado: se computa con ``Decimal`` y nunca se
persiste.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Literal

from app.domain.calculations import round_money

ZERO = Decimal("0.00")
HUNDRED = Decimal("100")

WARNING_THRESHOLD = Decimal("80")
CRITICAL_THRESHOLD = Decimal("90")
OVER_THRESHOLD = Decimal("100")

BudgetAlertLevel = Literal["OK", "WARNING", "CRITICAL", "OVER", "N/A"]

# Niveles que representan riesgo de sobregiro (excluyen OK y N/A).
ALERTING_LEVELS: frozenset[BudgetAlertLevel] = frozenset({"WARNING", "CRITICAL", "OVER"})


def compute_utilization_pct(actual: Decimal, budgeted: Decimal) -> Decimal | None:
    """Utilización = actual / budgeted * 100, cuantizada a 2 decimales.

    Retorna ``None`` cuando el presupuesto es cero (sin base de cálculo);
    nunca lanza ``ZeroDivisionError``.
    """
    if budgeted == ZERO:
        return None
    return round_money(actual / budgeted * HUNDRED)


def alert_level_for(pct: Decimal | None) -> BudgetAlertLevel:
    """Clasifica la utilización en el nivel de alerta correspondiente."""
    if pct is None:
        return "N/A"
    if pct < WARNING_THRESHOLD:
        return "OK"
    if pct < CRITICAL_THRESHOLD:
        return "WARNING"
    if pct < OVER_THRESHOLD:
        return "CRITICAL"
    return "OVER"


__all__ = [
    "ALERTING_LEVELS",
    "BudgetAlertLevel",
    "CRITICAL_THRESHOLD",
    "OVER_THRESHOLD",
    "WARNING_THRESHOLD",
    "alert_level_for",
    "compute_utilization_pct",
]
