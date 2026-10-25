"""Punto de entrada del backend de FacturaLibre."""

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from app.api.v1 import (
    accounting,
    assets,
    auth,
    banks,
    contacts,
    dashboard,
    employees,
    expenses,
    inventory,
    invoices,
    items,
    payments,
    payroll,
    pos,
    purchases,
    quotes,
    reports,
    settings,
    taxes,
    treasury,
    warehouses,
)
from app.application.accounting.period_service import FiscalPeriodError
from app.application.accounting.service import AccountingPeriodClosedError
from app.domain.exceptions import (
    FixedAssetError,
    FixedAssetValidationError,
    InventoryError,
    InvoiceStateError,
    InvoiceValidationError,
    PayrollError,
    QuoteStateError,
    ResourceNotFoundError,
    TreasuryError,
    TreasuryValidationError,
    VersionConflictError,
)

app = FastAPI(title="FacturaLibre API", version="0.1.0")

app.include_router(auth.router, prefix="/api/v1")
app.include_router(dashboard.router, prefix="/api/v1")
app.include_router(contacts.router, prefix="/api/v1")
app.include_router(items.router, prefix="/api/v1")
app.include_router(taxes.router, prefix="/api/v1")
app.include_router(invoices.router, prefix="/api/v1")
app.include_router(payments.router, prefix="/api/v1")
app.include_router(accounting.router, prefix="/api/v1")
app.include_router(assets.router, prefix="/api/v1")
app.include_router(warehouses.router, prefix="/api/v1")
app.include_router(expenses.router, prefix="/api/v1")
app.include_router(inventory.router, prefix="/api/v1")
app.include_router(employees.router, prefix="/api/v1")
app.include_router(payroll.router, prefix="/api/v1")
app.include_router(pos.router, prefix="/api/v1")
app.include_router(purchases.router, prefix="/api/v1")
app.include_router(quotes.router, prefix="/api/v1")
app.include_router(reports.router, prefix="/api/v1")
app.include_router(settings.router, prefix="/api/v1")
app.include_router(treasury.router, prefix="/api/v1")
app.include_router(banks.router, prefix="/api/v1")


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


@app.exception_handler(InvoiceValidationError)
async def invoice_validation_handler(
    _request: Request,
    exc: InvoiceValidationError,
) -> JSONResponse:
    """Traduce datos inválidos de una factura a un 422."""
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content={"detail": str(exc)},
    )


@app.exception_handler(QuoteStateError)
async def quote_state_handler(
    _request: Request,
    exc: QuoteStateError,
) -> JSONResponse:
    """Traduce una transición de estado inválida de cotización a un 409."""
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={"detail": str(exc)},
    )


@app.exception_handler(InventoryError)
async def inventory_error_handler(
    _request: Request,
    exc: InventoryError,
) -> JSONResponse:
    """Traduce stock insuficiente o bodega inactiva a un 409."""
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={"detail": str(exc)},
    )


@app.exception_handler(PayrollError)
async def payroll_error_handler(
    _request: Request,
    exc: PayrollError,
) -> JSONResponse:
    """Traduce un periodo ya liquidado o sin empleados a un 409."""
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={"detail": str(exc)},
    )


@app.exception_handler(TreasuryValidationError)
async def treasury_validation_handler(
    _request: Request,
    exc: TreasuryValidationError,
) -> JSONResponse:
    """Traduce datos inconsistentes de tesorería a un 422."""
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content={"detail": str(exc)},
    )


@app.exception_handler(TreasuryError)
async def treasury_error_handler(
    _request: Request,
    exc: TreasuryError,
) -> JSONResponse:
    """Traduce un conflicto de tesorería a un 409."""
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={"detail": str(exc)},
    )


@app.exception_handler(FixedAssetValidationError)
async def fixed_asset_validation_handler(
    _request: Request,
    exc: FixedAssetValidationError,
) -> JSONResponse:
    """Traduce datos inválidos de un activo a un 422."""
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content={"detail": str(exc)},
    )


@app.exception_handler(FixedAssetError)
async def fixed_asset_error_handler(
    _request: Request,
    exc: FixedAssetError,
) -> JSONResponse:
    """Traduce un conflicto de activos fijos a un 409."""
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={"detail": str(exc)},
    )


@app.exception_handler(AccountingPeriodClosedError)
async def accounting_period_closed_handler(
    _request: Request,
    exc: AccountingPeriodClosedError,
) -> JSONResponse:
    """Rechaza asientos nuevos en un periodo cerrado con un 409."""
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={"detail": str(exc)},
    )


@app.exception_handler(FiscalPeriodError)
async def fiscal_period_error_handler(
    _request: Request,
    exc: FiscalPeriodError,
) -> JSONResponse:
    """Traduce un cierre inválido o repetido a un 409."""
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={"detail": str(exc)},
    )


@app.get("/health", tags=["health"])
def health() -> dict[str, str]:
    """Comprueba que el proceso está vivo. No toca la base de datos."""
    return {"status": "ok"}
