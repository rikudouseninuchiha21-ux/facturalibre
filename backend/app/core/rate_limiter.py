"""Rate limiting en memoria (ventana fija) para intentos de login.

Suficiente para un solo proceso; en despliegues multi-worker se sustituye
el almacenamiento por Redis sin cambiar la interfaz.
"""

from __future__ import annotations

from collections import defaultdict
from time import monotonic

from app.core.config import get_settings

# El límite de intentos no aplica en el entorno de tests: la suite corre en
# un solo proceso (misma IP) y agotaría la ventana en el primer login. Los
# tests del limiter lo activan explícitamente con monkeypatch.
RATE_LIMIT_ENABLED = get_settings().environment.strip().lower() != "test"


class RateLimiter:
    """Límite de ``max_attempts`` por ``window_seconds`` para cada clave."""

    def __init__(self, *, max_attempts: int, window_seconds: int) -> None:
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self._attempts: dict[str, list[float]] = defaultdict(list)

    def check(self, key: str) -> tuple[bool, int]:
        """Indica si la clave puede intentar y en cuántos segundos reintenta."""
        now = monotonic()
        attempts = [stamp for stamp in self._attempts[key] if now - stamp < self.window_seconds]
        self._attempts[key] = attempts
        if len(attempts) >= self.max_attempts:
            retry_after = int(self.window_seconds - (now - attempts[0])) + 1
            return False, retry_after
        self._attempts[key].append(now)
        return True, 0


LOGIN_LIMITER = RateLimiter(max_attempts=5, window_seconds=60)


def login_rate_limiter() -> RateLimiter:
    """Instancia configurada por entorno (tests inyectan una limpia)."""
    return LOGIN_LIMITER


__all__ = ["RATE_LIMIT_ENABLED", "RateLimiter", "login_rate_limiter"]
