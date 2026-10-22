"""Punto de entrada del backend de FacturaLibre."""

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from app.api.v1 import accounting, contacts, invoices, items, payments, taxes
from app.domain.exceptions import (
    InvoiceStateError,
    ResourceNotFoundError,
    VersionConflictError,
)

app = FastAPI(title="FacturaLibre API", version="0.1.0")

app.include_router(contacts.router, prefix="/api/v1")
app.include_router(items.router, prefix="/api/v1")
app.include_router(taxes.router, prefix="/api/v1")
app.include_router(invoices.router, prefix="/api/v1")
app.include_router(payments.router, prefix="/api/v1")
app.include_router(accounting.router, prefix="/api/v1")


@app.exception_handler(ResourceNotFoundError)
async def resource_not_found_handler(
    _request: Request,
    exc: ResourceNotFoundError,
) -> JSONResponse:
    """Traduce un recurso ausente a un 404 con detalle legible."""
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={"detail": str(exc)},
    )


@app.exception_handler(VersionConflictError)
async def version_conflict_handler(
    _request: Request,
    exc: VersionConflictError,
) -> JSONResponse:
    """Traduce una versión obsoleta a un 409 de conflicto."""
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={"detail": str(exc)},
    )


@app.exception_handler(InvoiceStateError)
async def invoice_state_handler(
    _request: Request,
    exc: InvoiceStateError,
) -> JSONResponse:
    """Traduce una transición de estado inválida a un 409."""
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={"detail": str(exc)},
    )


@app.get("/health", tags=["health"])
def health() -> dict[str, str]:
    """Comprueba que el proceso está vivo. No toca la base de datos."""
    return {"status": "ok"}
