"""Pruebas del CRM: Kanban, actividades, conversión y aislamiento."""

from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.models.company import Company
from app.domain.models.contact import Contact
from app.domain.models.crm import CrmOpportunity, CrmStage
from app.domain.models.quote import Quote


def _stages(client: TestClient) -> dict[str, dict]:
    response = client.get("/api/v1/crm/stages")
    assert response.status_code == 200, response.text
    return {stage["name"]: stage for stage in response.json()}


def _contact(client: TestClient, name: str = "Cliente CRM") -> dict:
    response = client.post("/api/v1/contacts", json={"name": name})
    assert response.status_code == 201, response.text
    return response.json()


def _opportunity(
    client: TestClient,
    *,
    contact_id: str,
    stage_id: str,
    title: str = "Renovación anual",
    amount: str = "1500.50",
) -> dict:
    response = client.post(
        "/api/v1/crm/opportunities",
        json={
            "contact_id": contact_id,
            "stage_id": stage_id,
            "title": title,
            "amount": amount,
            "expected_close_date": "2099-12-31",
            "notes": "Oportunidad de prueba",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_new_company_gets_default_crm_stages(client: TestClient) -> None:
    response = client.post(
        "/api/v1/companies",
        json={"name": "CRM Nueva S.A.S.", "tax_id": "901333222-1"},
    )
    assert response.status_code == 201, response.text
    company = response.json()

    response = client.post(f"/api/v1/auth/switch-company/{company['id']}")
    assert response.status_code == 200, response.text

    stages = client.get("/api/v1/crm/stages")
    assert stages.status_code == 200, stages.text
    assert [stage["name"] for stage in stages.json()] == [
        "Nuevo Lead",
        "Contactado",
        "Propuesta",
        "Negociación",
        "Ganado",
        "Perdido",
    ]


def test_create_and_move_opportunity(client: TestClient) -> None:
    stages = _stages(client)
    contact = _contact(client)
    opportunity = _opportunity(
        client,
        contact_id=contact["id"],
        stage_id=stages["Nuevo Lead"]["id"],
    )

    assert opportunity["contact_name"] == "Cliente CRM"
    assert opportunity["stage_name"] == "Nuevo Lead"
    assert opportunity["amount"] == "1500.50"
    assert opportunity["owner_name"]

    response = client.patch(
        f"/api/v1/crm/opportunities/{opportunity['id']}/move",
        json={"stage_id": stages["Contactado"]["id"]},
    )
    assert response.status_code == 200, response.text
    moved = response.json()
    assert moved["stage_id"] == stages["Contactado"]["id"]
    assert moved["stage_name"] == "Contactado"
    assert moved["is_won"] is False
    assert moved["is_lost"] is False


def test_winning_and_losing_stages_update_outcome(client: TestClient) -> None:
    stages = _stages(client)
    contact = _contact(client)
    opportunity = _opportunity(
        client,
        contact_id=contact["id"],
        stage_id=stages["Propuesta"]["id"],
    )

    response = client.patch(
        f"/api/v1/crm/opportunities/{opportunity['id']}/move",
        json={"stage_id": stages["Ganado"]["id"]},
    )
    assert response.status_code == 200, response.text
    won = response.json()
    assert won["is_won"] is True
    assert won["is_lost"] is False

    response = client.patch(
        f"/api/v1/crm/opportunities/{opportunity['id']}/move",
        json={"stage_id": stages["Perdido"]["id"]},
    )
    assert response.status_code == 200, response.text
    lost = response.json()
    assert lost["is_lost"] is True
    assert lost["is_won"] is False


def test_activity_appears_in_history(client: TestClient) -> None:
    stages = _stages(client)
    contact = _contact(client)
    opportunity = _opportunity(
        client,
        contact_id=contact["id"],
        stage_id=stages["Contactado"]["id"],
    )

    response = client.post(
        f"/api/v1/crm/opportunities/{opportunity['id']}/activities",
        json={
            "type": "CALL",
            "description": "Llamada para confirmar presupuesto",
        },
    )
    assert response.status_code == 201, response.text
    activity = response.json()
    assert activity["type"] == "CALL"
    assert activity["created_by_name"]

    detail = client.get(f"/api/v1/crm/opportunities/{opportunity['id']}")
    assert detail.status_code == 200, detail.text
    activities = detail.json()["activities"]
    assert len(activities) == 1
    assert activities[0]["description"] == "Llamada para confirmar presupuesto"


def test_convert_opportunity_to_quote(
    client: TestClient,
    db_session: Session,
) -> None:
    stages = _stages(client)
    contact = _contact(client, "Cliente Conversión")
    opportunity = _opportunity(
        client,
        contact_id=contact["id"],
        stage_id=stages["Negociación"]["id"],
        title="Implementación VANTAGE",
        amount="2500.00",
    )

    response = client.post(f"/api/v1/crm/opportunities/{opportunity['id']}/convert-to-quote")
    assert response.status_code == 200, response.text
    converted = response.json()
    assert converted["quote_id"] is not None

    quote = db_session.scalar(select(Quote).where(Quote.id == UUID(converted["quote_id"])))
    assert quote is not None
    assert quote.status.value == "DRAFT"
    assert quote.contact_id == UUID(contact["id"])
    assert quote.subtotal == Decimal("2500.00")
    assert quote.tax_total == Decimal("0.00")
    assert quote.total == Decimal("2500.00")
    assert len(quote.lines) == 1
    assert quote.lines[0].item_id is None
    assert quote.lines[0].description == "Implementación VANTAGE"

    # Una segunda conversión no duplica la cotización.
    duplicate = client.post(f"/api/v1/crm/opportunities/{opportunity['id']}/convert-to-quote")
    assert duplicate.status_code == 409


def test_opportunities_are_isolated_between_companies(
    client: TestClient,
    db_session: Session,
) -> None:
    stages = _stages(client)
    contact_a = _contact(client, "Cliente Empresa A")
    opportunity_a = _opportunity(
        client,
        contact_id=contact_a["id"],
        stage_id=stages["Nuevo Lead"]["id"],
        title="Oportunidad A",
    )
    me = client.get("/api/v1/auth/me").json()

    company_b = Company(name="Empresa B CRM S.A.S.", tax_id="901777666-5")
    db_session.add(company_b)
    db_session.flush()
    stage_b = CrmStage(
        company_id=company_b.id,
        name="Etapa B",
        order=1,
        color="#3b82f6",
    )
    contact_b = Contact(company_id=company_b.id, name="Cliente Empresa B")
    db_session.add_all([stage_b, contact_b])
    db_session.flush()
    opportunity_b = CrmOpportunity(
        company_id=company_b.id,
        contact_id=contact_b.id,
        stage_id=stage_b.id,
        owner_id=UUID(me["id"]),
        title="Oportunidad B",
        amount=Decimal("999.00"),
    )
    db_session.add(opportunity_b)
    db_session.flush()

    response = client.get("/api/v1/crm/opportunities")
    assert response.status_code == 200, response.text
    ids = {item["id"] for item in response.json()}
    assert opportunity_a["id"] in ids
    assert str(opportunity_b.id) not in ids

    response = client.get(f"/api/v1/crm/opportunities/{opportunity_b.id}")
    assert response.status_code == 404
