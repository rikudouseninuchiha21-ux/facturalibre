"""Registro de consentimientos GDPR/CCPA y textos legales (Fase 39B)."""

from __future__ import annotations

from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Request, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.api.dependencies.auth import get_current_user_optional
from app.domain.models.auth import User
from app.domain.models.consent import UserConsent
from app.infrastructure.database import get_db

CurrentUserOptional = Depends(get_current_user_optional)

router = APIRouter(tags=["privacy"])

DbSession = Annotated[Session, Depends(get_db)]

CONSENT_TYPES: tuple[str, ...] = (
    "cookies_essential",
    "cookies_analytics",
    "cookies_marketing",
    "terms_of_service",
)

PRIVACY_POLICY_TEXT = """# Política de Privacidad — VANTAGE

VANTAGE recopila únicamente los datos necesarios para prestar el servicio
de facturación, contabilidad y nómina. Las cookies esenciales mantienen la
sesión iniciada; las analíticas y de marketing son opcionales y se activan
solo con tu consentimiento explícito (Ley 1581 de 2012, GDPR y CCPA).

Puedes revocar tu consentimiento en cualquier momento escribiendo a
privacidad@vantage.co. No vendemos datos personales a terceros y los
consentimientos quedan registrados con fecha, IP y agente de usuario como
evidencia de cumplimiento."""

TERMS_OF_SERVICE_TEXT = """# Términos y Condiciones — VANTAGE

El uso de VANTAGE implica la aceptación de estos términos: el titular
de la cuenta es responsable de la veracidad de los datos fiscales
registrados (facturación electrónica DIAN, nómina y contabilidad) y de la
custodia de sus credenciales. El servicio se presta tal como está, con
esfuerzos razonables de disponibilidad y respaldo. Estos términos se
rigen por la legislación colombiana."""


class ConsentRequest(BaseModel):
    """Consentimiento otorgado o rechazado por tipo."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    consent_type: Literal[
        "cookies_essential", "cookies_analytics", "cookies_marketing", "terms_of_service"
    ]
    is_granted: bool = True


class ConsentRead(BaseModel):
    """Confirmación del consentimiento registrado."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    consent_type: str
    is_granted: bool


@router.post(
    "/consent",
    response_model=ConsentRead,
    status_code=status.HTTP_201_CREATED,
)
def register_consent(
    payload: ConsentRequest,
    request: Request,
    db: DbSession,
    current_user: User | None = CurrentUserOptional,
) -> ConsentRead:
    """Registra el consentimiento con IP y user-agent como evidencia.

    Público: los visitantes anónimos también consienten cookies; el
    usuario autenticado se vincula con su id (nullable en la tabla).
    """
    consent = UserConsent(
        user_id=current_user.id if current_user is not None else None,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent", "")[:255],
        consent_type=payload.consent_type,
        is_granted=payload.is_granted,
    )
    db.add(consent)
    db.flush()
    return ConsentRead.model_validate(consent)


@router.get("/privacy-policy")
def get_privacy_policy() -> dict[str, str]:
    """Texto de la política de privacidad (público, no requiere sesión)."""
    return {"title": "Política de Privacidad", "body": PRIVACY_POLICY_TEXT}


@router.get("/terms")
def get_terms() -> dict[str, str]:
    """Texto de los términos y condiciones (público)."""
    return {"title": "Términos y Condiciones", "body": TERMS_OF_SERVICE_TEXT}


__all__ = ["router"]
