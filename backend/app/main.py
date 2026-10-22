"""Punto de entrada mínimo del backend de FacturaLibre."""

from fastapi import FastAPI

app = FastAPI(title="FacturaLibre API", version="0.1.0")


@app.get("/health", tags=["health"])
def health() -> dict[str, str]:
    """Comprueba que el proceso está vivo. No toca la base de datos."""
    return {"status": "ok"}
