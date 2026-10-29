"""Punto de entrada del backend de FacturaLibre."""

from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from app.api.v1 import (
    accounting,
    assets,
    auth,
    banks,
    budgets,
    companies,
    consent,
    contacts,
    cost_centers,
    dashboard,
    employees,
    expenses,
    inventory,
    invoice_documents,
    invoices,
    items,
    notifications,
    payments,
    payroll,
    pos,
    purchases,
    quotes,
    receivables,
    reports,
    settings,
    taxes,
    treasury,
    users,
    warehouses,
)
from app.application.accounting.period_service import FiscalPeriodError
from app.application.accounting.service import AccountingPeriodClosedError
from app.domain.exceptions import (
    AgreementError,
    AgreementValidationError,
    BudgetError,
    BudgetStateError,
    BudgetValidationError,
    CostCenterError,
    DianError,
    DianStateError,
    DianValidationError,
    FixedAssetError,
    FixedAssetValidationError,
    InventoryError,
    InvoiceStateError,
    InvoiceValidationError,
    PayrollError,
    QuoteStateError,
    ReceivablesError,
    ReceivablesValidationError,
    ReminderError,
    ResourceNotFoundError,
    TreasuryError,
    TreasuryValidationError,
    VersionConflictError,
)

app = FastAPI(title="FacturaLibre API", version="0.1.0")

# -- Hardening (Fase 39B): cabeceras de seguridad en toda respuesta. -------
SECURITY_HEADERS: dict[str, str] = {
    "Content-Security-Policy": (
        "default-src 'self'; frame-ancestors 'none'; base-uri 'self'; "
        "form-action 'self'; object-src 'none'"
    ),
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
    "X-Frame-Options": "DENY",
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "strict-origin-when-cross-origin",
}


@app.middleware("http")
async def security_headers_middleware(request: Request, call_next: Any) -> Any:
    """Aplica las cabeceras OWASP de cabecera a cada respuesta."""
    response = await call_next(request)
    for name, value in SECURITY_HEADERS.items():
        response.headers.setdefault(name, value)
    return response


from fastapi.middleware.cors import CORSMiddleware  # noqa: E402

from app.core.config import get_settings  # noqa: E402

_settings = get_settings()
# CORS restringido a orígenes exactos (nunca ``*``): el frontend usa rewrites
# same-origin, por lo que por defecto solo se habilita el origen de desarrollo.
_allowed_origins = ["http://localhost:3000", "http://127.0.0.1:3000"]
if _settings.environment.strip().lower() in {"production", "prod"}:
    _allowed_origins = ["https://app.nexuserp.co"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/v1")
app.include_router(companies.router, prefix="/api/v1")
app.include_router(consent.router, prefix="/api/v1")
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
app.include_router(users.router, prefix="/api/v1")
app.include_router(treasury.router, prefix="/api/v1")
app.include_router(banks.router, prefix="/api/v1")
app.include_router(cost_centers.router, prefix="/api/v1")
app.include_router(budgets.router, prefix="/api/v1")
app.include_router(notifications.router, prefix="/api/v1")
app.include_router(receivables.router, prefix="/api/v1")
app.include_router(invoice_documents.router, prefix="/api/v1")


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


@app.exception_handler(CostCenterError)
async def cost_center_error_handler(
    _request: Request,
    exc: CostCenterError,
) -> JSONResponse:
    """Traduce un conflicto de centro de costo (código duplicado) a un 409."""
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={"detail": str(exc)},
    )


@app.exception_handler(BudgetStateError)
async def budget_state_error_handler(
    _request: Request,
    exc: BudgetStateError,
) -> JSONResponse:
    """Traduce una transición inválida de presupuesto a un 409."""
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={"detail": str(exc)},
    )


@app.exception_handler(BudgetValidationError)
async def budget_validation_error_handler(
    _request: Request,
    exc: BudgetValidationError,
) -> JSONResponse:
    """Traduce datos de presupuesto inconsistentes a un 422."""
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content={"detail": str(exc)},
    )


@app.exception_handler(BudgetError)
async def budget_error_handler(
    _request: Request,
    exc: BudgetError,
) -> JSONResponse:
    """Traduce un conflicto de presupuesto (periodo duplicado) a un 409."""
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={"detail": str(exc)},
    )


@app.exception_handler(ReceivablesValidationError)
async def receivables_validation_handler(
    _request: Request,
    exc: ReceivablesValidationError,
) -> JSONResponse:
    """Traduce datos de cartera inválidos a un 422."""
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content={"detail": str(exc)},
    )


@app.exception_handler(AgreementValidationError)
async def agreement_validation_handler(
    _request: Request,
    exc: AgreementValidationError,
) -> JSONResponse:
    """Traduce un acuerdo inconsistente con sus cuotas o saldo a un 422."""
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content={"detail": str(exc)},
    )


@app.exception_handler(ReminderError)
async def reminder_error_handler(
    _request: Request,
    exc: ReminderError,
) -> JSONResponse:
    """Traduce un recordatorio no permitido a un 409."""
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={"detail": str(exc)},
    )


@app.exception_handler(AgreementError)
async def agreement_error_handler(
    _request: Request,
    exc: AgreementError,
) -> JSONResponse:
    """Traduce una transición inválida de acuerdo de pago a un 409."""
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={"detail": str(exc)},
    )


@app.exception_handler(ReceivablesError)
async def receivables_error_handler(
    _request: Request,
    exc: ReceivablesError,
) -> JSONResponse:
    """Traduce un conflicto genérico de cartera a un 409."""
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={"detail": str(exc)},
    )


@app.exception_handler(DianValidationError)
async def dian_validation_handler(
    _request: Request,
    exc: DianValidationError,
) -> JSONResponse:
    """Traduce datos DIAN incompletos o inválidos a un 422."""
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content={"detail": str(exc)},
    )


@app.exception_handler(DianStateError)
async def dian_state_handler(
    _request: Request,
    exc: DianStateError,
) -> JSONResponse:
    """Traduce un documento DIAN sobre factura no emitida a un 409."""
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={"detail": str(exc)},
    )


@app.exception_handler(DianError)
async def dian_error_handler(
    _request: Request,
    exc: DianError,
) -> JSONResponse:
    """Traduce un conflicto genérico del documento DIAN a un 409."""
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={"detail": str(exc)},
    )


@app.get("/health", tags=["health"])
def health() -> dict[str, str]:
    """Comprueba que el proceso está vivo. No toca la base de datos."""
    return {"status": "ok"}
