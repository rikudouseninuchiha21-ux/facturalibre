"""Tests de la dimensión centro de costo en el servicio de asientos."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.application.accounting.service import AccountingService, JournalLine
from app.domain.models.accounting import AccountingEntryLine, AccountingSourceType


def _create_cost_center(client: TestClient) -> UUID:
    response = client.post(
        "/api/v1/cost-centers",
        json={"code": f"CC-{uuid4().hex[:8].upper()}", "name": "Journal"},
    )
    assert response.status_code == 201, response.text
    return UUID(str(response.json()["id"]))


def test_post_entry_persists_cost_center_per_line(
    client: TestClient,
    db_session: Session,
) -> None:
    """Cada línea persiste su propio cost_center_id; NULL si no se etiqueta."""
    center_id = _create_cost_center(client)
    service = AccountingService(db_session)

    entry = service._post_entry(
        entry_date=date.today(),
        description="Asiento con dimensión de centro de costo",
        source_type=AccountingSourceType.INVOICE,
        source_id=uuid4(),
        lines=[
            JournalLine(account_code="5199", debit=Decimal("100.00"), cost_center_id=center_id),
            JournalLine(account_code="110505", credit=Decimal("100.00")),
        ],
    )

    lines = {line.account_code: line for line in entry.lines}
    assert lines["5199"].cost_center_id == center_id
    assert lines["110505"].cost_center_id is None


def test_default_lines_have_null_cost_center(
    client: TestClient,
    db_session: Session,
) -> None:
    """Sin la dimensión, el comportamiento previo queda intacto (NULL)."""
    service = AccountingService(db_session)

    entry = service._post_entry(
        entry_date=date.today(),
        description="Asiento histórico sin centro de costo",
        source_type=AccountingSourceType.INVOICE,
        source_id=uuid4(),
        lines=[
            JournalLine(account_code="5199", debit=Decimal("50.00")),
            JournalLine(account_code="110505", credit=Decimal("50.00")),
        ],
    )

    for line in entry.lines:
        assert line.cost_center_id is None

    persisted = db_session.scalars(
        select(AccountingEntryLine).where(AccountingEntryLine.entry_id == entry.id)
    ).all()
    assert all(line.cost_center_id is None for line in persisted)
