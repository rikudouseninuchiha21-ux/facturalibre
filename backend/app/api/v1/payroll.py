"""Rutas de periodos y liquidación de nómina."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.dependencies.auth import get_current_user, require_role
from app.application.payroll.document_service import PayrollDocumentService
from app.application.payroll.schemas import PayrollPeriodCreate, PayrollPeriodRead
from app.application.payroll.service import PayrollService
from app.domain.cost_center_repository import CostCenterRepository
from app.domain.exceptions import ResourceNotFoundError
from app.domain.models.auth import UserRole
from app.domain.payroll_repository import PayrollRepository
from app.infrastructure.database import get_db
from app.infrastructure.transactions import operation_transaction

router = APIRouter(
    prefix="/payroll",
    tags=["payroll"],
    dependencies=[Depends(get_current_user)],
)

# El rol pasa a declararse por ruta: los documentos de nómina se comparten
# con ACCOUNTANT (y el PDF con CASHIER), mientras el CRUD sigue en ADMIN.
ADMIN = [UserRole.ADMIN]
READ_DOCUMENTS = [UserRole.ADMIN, UserRole.ACCOUNTANT]
READ_PDF = [UserRole.ADMIN, UserRole.ACCOUNTANT, UserRole.CASHIER]

DbSession = Annotated[Session, Depends(get_db)]
PERIOD_CONFLICT = "Ya existe un periodo de nómina para ese mes y año"


def get_payroll_repository(db: DbSession) -> PayrollRepository:
    """Construye el repositorio con la sesión de la petición."""
    return PayrollRepository(db)


PayrollRepositoryDep = Annotated[PayrollRepository, Depends(get_payroll_repository)]


@router.post(
    "/periods",
    response_model=PayrollPeriodRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_role(ADMIN))],
)
def create_period(
    payload: PayrollPeriodCreate,
    db: DbSession,
    repository: PayrollRepositoryDep,
) -> PayrollPeriodRead:
    """Abre un periodo mensual de nómina en estado DRAFT."""
    if payload.cost_center_id is not None:
        cost_center = CostCenterRepository(db).get_by_id(payload.cost_center_id)
        if cost_center is None or not cost_center.is_active:
            raise HTTPException(
                status_code=422,
                detail="cost_center_id no existe o está inactivo",
            )
    try:
        period = repository.create_period(payload.model_dump())
    except IntegrityError:
        repository.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=PERIOD_CONFLICT,
        ) from None
    return PayrollPeriodRead.model_validate(period)


@router.get(
    "/periods",
    response_model=list[PayrollPeriodRead],
    dependencies=[Depends(require_role(ADMIN))],
)
def list_periods(
    repository: PayrollRepositoryDep,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[PayrollPeriodRead]:
    """Lista los periodos de nómina con su detalle."""
    periods = repository.list(limit=limit, offset=offset)
    return [PayrollPeriodRead.model_validate(period) for period in periods]


@router.post(
    "/periods/{period_id}/calculate",
    response_model=PayrollPeriodRead,
    dependencies=[Depends(require_role(ADMIN))],
)
def calculate_period(
    period_id: UUID,
    db: DbSession,
) -> PayrollPeriodRead:
    """Calcula la nómina y genera el asiento contable de forma atómica."""
    with operation_transaction(db):
        period = PayrollService(db).calculate_period(period_id)
    return PayrollPeriodRead.model_validate(period)


@router.get(
    "/periods/{period_id}",
    response_model=PayrollPeriodRead,
    dependencies=[Depends(require_role(READ_DOCUMENTS))],
)
def get_period(
    period_id: UUID,
    repository: PayrollRepositoryDep,
) -> PayrollPeriodRead:
    """Consulta el detalle calculado de un periodo."""
    period = repository.get_by_id(period_id)
    if period is None:
        raise ResourceNotFoundError("Periodo de nómina no encontrado")
    return PayrollPeriodRead.model_validate(period)


def get_payroll_document_service(db: DbSession) -> PayrollDocumentService:
    """Construye el servicio de documentos de nómina de la petición."""
    return PayrollDocumentService(db)


PayrollDocumentServiceDep = Annotated[
    PayrollDocumentService,
    Depends(get_payroll_document_service),
]


def _document_name(period, extension: str) -> str:
    return f"NE-{period.year}-{period.month:02d}.{extension}"


@router.get(
    "/periods/{period_id}/xml",
    response_class=Response,
    dependencies=[Depends(require_role(READ_DOCUMENTS))],
)
def download_period_xml(
    period_id: UUID,
    db: DbSession,
    service: PayrollDocumentServiceDep,
) -> Response:
    """XML UBL 2.1 de nómina electrónica del periodo (sin firma, sin envío)."""
    period, company, rows, employees = service.load_period(period_id)
    with operation_transaction(db):
        cune = service.ensure_generated(period, company, rows, employees)
    xml_bytes = service.build_xml(period, company, rows, employees, cune)
    return Response(
        content=xml_bytes,
        media_type="application/xml",
        headers={"Content-Disposition": f'attachment; filename="{_document_name(period, "xml")}"'},
    )


@router.get(
    "/periods/{period_id}/pdf",
    response_class=Response,
    dependencies=[Depends(require_role(READ_PDF))],
)
def download_period_pdf(
    period_id: UUID,
    db: DbSession,
    service: PayrollDocumentServiceDep,
) -> Response:
    """PDF del comprobante de nómina electrónica del periodo."""
    from app.application.payroll.pdf_builder import build_payroll_pdf

    period, company, rows, employees = service.load_period(period_id)
    with operation_transaction(db):
        cune = service.ensure_generated(period, company, rows, employees)
    pdf_bytes = build_payroll_pdf(
        period=period,
        company=company,
        rows=rows,
        employees=employees,
        cune=cune,
        generation_date=service.generation_date(period),
        environment=company.dian_environment,
    )
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{_document_name(period, "pdf")}"'},
    )


@router.get(
    "/periods/{period_id}/pila",
    response_class=Response,
    dependencies=[Depends(require_role(READ_DOCUMENTS))],
)
def download_period_pila(
    period_id: UUID,
    service: PayrollDocumentServiceDep,
) -> Response:
    """Archivo plano PILA del periodo."""
    period, company, rows, employees = service.load_period(period_id)
    pila = service.build_pila(period, company, rows, employees)
    return Response(
        content=pila,
        media_type="text/plain; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{_document_name(period, "pila")}"'},
    )


@router.get(
    "/periods/{period_id}/ugpp",
    dependencies=[Depends(require_role(ADMIN))],
)
def get_period_ugpp(
    period_id: UUID,
    service: PayrollDocumentServiceDep,
) -> dict[str, object]:
    """Resumen UGPP de aportes por empleado y totales del periodo."""
    _period, _company, rows, employees = service.load_period(period_id)
    return service.build_ugpp(_period, rows, employees)


@router.post(
    "/periods/{period_id}/regenerate-cune",
    dependencies=[Depends(require_role(ADMIN))],
)
def regenerate_period_cune(
    period_id: UUID,
    db: DbSession,
    service: PayrollDocumentServiceDep,
) -> dict[str, object]:
    """Recalcula y persiste el CUNE del periodo (p. ej. tras cambiar el PIN)."""
    period, company, rows, employees = service.load_period(period_id)
    with operation_transaction(db):
        cune = service.ensure_generated(period, company, rows, employees)
    return {
        "period_id": str(period.id),
        "cune": cune,
        "dian_status": period.dian_status.value if period.dian_status else None,
    }


__all__ = ["router"]
