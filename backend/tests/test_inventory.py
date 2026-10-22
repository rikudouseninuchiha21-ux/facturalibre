"""Tests de integración del módulo de inventarios con PostgreSQL real."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.domain.models.accounting import AccountingEntry
from app.domain.models.invoice import Invoice, LifecycleStatus
from app.domain.models.number_sequence import NumberSequence
from app.domain.models.stock import StockBalance, StockMovement, StockMovementType

TWOPLACES = Decimal("0.01")


def _money(value: object) -> Decimal:
    return Decimal(str(value)).quantize(TWOPLACES)


def _create_contact(client: TestClient) -> dict[str, Any]:
    response = client.post(
        "/api/v1/contacts",
        json={"name": "Cliente Inventario", "email": "inventario@example.com"},
    )
    assert response.status_code == 201, response.text
    return response.json()


def _create_item(client: TestClient) -> dict[str, Any]:
    response = client.post(
        "/api/v1/items",
        json={
            "name": "Producto inventariable",
            "description": "Producto inventariable",
            "unit_price": "50.00",
            "tax_id": None,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def _create_warehouse(
    client: TestClient,
    *,
    code: str = "PRINCIPAL",
    name: str = "Bodega principal",
) -> dict[str, Any]:
    response = client.post(
        "/api/v1/warehouses",
        json={"name": name, "code": code},
    )
    assert response.status_code == 201, response.text
    return response.json()


def _register_movement(
    client: TestClient,
    *,
    item_id: str,
    warehouse_id: str,
    movement_type: str,
    quantity: str,
    reference: str | None = None,
) -> Any:
    body: dict[str, Any] = {
        "item_id": item_id,
        "warehouse_id": warehouse_id,
        "movement_type": movement_type,
        "quantity": quantity,
    }
    if reference is not None:
        body["reference"] = reference
    return client.post("/api/v1/inventory/movements", json=body)


def _create_draft_invoice(
    client: TestClient,
    *,
    contact_id: str,
    item_id: str,
    quantities: list[str],
) -> Any:
    today = date.today()
    return client.post(
        "/api/v1/invoices",
        headers={"Idempotency-Key": str(uuid4())},
        json={
            "contact_id": contact_id,
            "issue_date": today.isoformat(),
            "due_date": (today + timedelta(days=30)).isoformat(),
            "currency": "COP",
            "lines": [
                {
                    "item_id": item_id,
                    "quantity": quantity,
                    "unit_price": "50.00",
                    "discount_percent": "0",
                }
                for quantity in quantities
            ],
        },
    )


def _balances(
    client: TestClient,
    *,
    warehouse_id: str,
    item_id: str,
) -> list[dict[str, Any]]:
    response = client.get(
        "/api/v1/inventory/balances",
        params={"warehouse_id": warehouse_id, "item_id": item_id},
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_warehouse_crud_and_incoming_movement_updates_balance(
    client: TestClient,
    db_session: Session,
) -> None:
    warehouse = _create_warehouse(client)
    item = _create_item(client)

    listed = client.get("/api/v1/warehouses")
    assert listed.status_code == 200
    assert [row["id"] for row in listed.json()] == [warehouse["id"]]

    updated = client.patch(
        f"/api/v1/warehouses/{warehouse['id']}",
        json={"name": "Bodega central"},
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["name"] == "Bodega central"

    movement = _register_movement(
        client,
        item_id=str(item["id"]),
        warehouse_id=str(warehouse["id"]),
        movement_type="IN",
        quantity="10.0000",
        reference="INV-001",
    )
    assert movement.status_code == 201, movement.text
    assert movement.json()["movement_type"] == "IN"
    assert movement.json()["reference"] == "INV-001"

    balances = _balances(
        client,
        warehouse_id=str(warehouse["id"]),
        item_id=str(item["id"]),
    )
    assert len(balances) == 1
    assert _money(balances[0]["quantity"]) == Decimal("10.00")
    assert balances[0]["warehouse_name"] == "Bodega central"

    stored = db_session.scalar(
        select(StockBalance).where(
            StockBalance.item_id == UUID(str(item["id"])),
            StockBalance.warehouse_id == UUID(str(warehouse["id"])),
        )
    )
    assert stored is not None
    assert _money(stored.quantity) == Decimal("10.00")


def test_transfer_and_adjustment_update_each_warehouse_balance(
    client: TestClient,
) -> None:
    source = _create_warehouse(client)
    destination = _create_warehouse(
        client,
        code="SECUNDARIA",
        name="Bodega secundaria",
    )
    item = _create_item(client)
    incoming = _register_movement(
        client,
        item_id=str(item["id"]),
        warehouse_id=str(source["id"]),
        movement_type="IN",
        quantity="10.0000",
    )
    assert incoming.status_code == 201, incoming.text

    transfer_out = _register_movement(
        client,
        item_id=str(item["id"]),
        warehouse_id=str(source["id"]),
        movement_type="TRANSFER_OUT",
        quantity="4.0000",
        reference="TRF-001",
    )
    assert transfer_out.status_code == 201, transfer_out.text
    transfer_in = _register_movement(
        client,
        item_id=str(item["id"]),
        warehouse_id=str(destination["id"]),
        movement_type="TRANSFER_IN",
        quantity="4.0000",
        reference="TRF-001",
    )
    assert transfer_in.status_code == 201, transfer_in.text
    adjustment = _register_movement(
        client,
        item_id=str(item["id"]),
        warehouse_id=str(destination["id"]),
        movement_type="ADJUSTMENT",
        quantity="1.0000",
    )
    assert adjustment.status_code == 201, adjustment.text

    source_balance = _balances(
        client,
        warehouse_id=str(source["id"]),
        item_id=str(item["id"]),
    )
    destination_balance = _balances(
        client,
        warehouse_id=str(destination["id"]),
        item_id=str(item["id"]),
    )
    assert _money(source_balance[0]["quantity"]) == Decimal("6.00")
    assert _money(destination_balance[0]["quantity"]) == Decimal("5.00")


def test_outgoing_movement_without_stock_fails_without_side_effects(
    client: TestClient,
    db_session: Session,
) -> None:
    warehouse = _create_warehouse(client)
    item = _create_item(client)

    response = _register_movement(
        client,
        item_id=str(item["id"]),
        warehouse_id=str(warehouse["id"]),
        movement_type="OUT",
        quantity="1.0000",
    )

    assert response.status_code == 409
    assert "Stock insuficiente" in response.json()["detail"]
    assert (
        _balances(
            client,
            warehouse_id=str(warehouse["id"]),
            item_id=str(item["id"]),
        )
        == []
    )
    assert db_session.scalar(select(func.count()).select_from(StockMovement)) == 0
    assert db_session.scalar(select(func.count()).select_from(StockBalance)) == 0


def test_issue_invoice_generates_out_movements_and_lowers_stock(
    client: TestClient,
    db_session: Session,
) -> None:
    warehouse = _create_warehouse(client)
    item = _create_item(client)
    contact = _create_contact(client)
    incoming = _register_movement(
        client,
        item_id=str(item["id"]),
        warehouse_id=str(warehouse["id"]),
        movement_type="IN",
        quantity="10.0000",
    )
    assert incoming.status_code == 201, incoming.text

    draft = _create_draft_invoice(
        client,
        contact_id=str(contact["id"]),
        item_id=str(item["id"]),
        quantities=["3.0000", "2.0000"],
    )
    assert draft.status_code == 201, draft.text

    issued = client.post(f"/api/v1/invoices/{draft.json()['id']}/issue")
    assert issued.status_code == 200, issued.text

    balances = _balances(
        client,
        warehouse_id=str(warehouse["id"]),
        item_id=str(item["id"]),
    )
    assert len(balances) == 1
    assert _money(balances[0]["quantity"]) == Decimal("5.00")

    out_movements = list(
        db_session.scalars(
            select(StockMovement).where(
                StockMovement.item_id == UUID(str(item["id"])),
                StockMovement.movement_type == StockMovementType.OUT,
            )
        ).all()
    )
    assert len(out_movements) == 2
    assert {_money(movement.quantity) for movement in out_movements} == {
        Decimal("3.00"),
        Decimal("2.00"),
    }
    assert {movement.reference for movement in out_movements} == {issued.json()["number"]}


def test_issue_invoice_without_stock_rolls_back_invoice_and_movements(
    client: TestClient,
    db_session: Session,
) -> None:
    warehouse = _create_warehouse(client)
    item = _create_item(client)
    contact = _create_contact(client)
    draft = _create_draft_invoice(
        client,
        contact_id=str(contact["id"]),
        item_id=str(item["id"]),
        quantities=["1.0000"],
    )
    assert draft.status_code == 201, draft.text
    invoice_id = draft.json()["id"]

    response = client.post(f"/api/v1/invoices/{invoice_id}/issue")

    assert response.status_code == 409
    assert "Stock insuficiente" in response.json()["detail"]

    unchanged = client.get(f"/api/v1/invoices/{invoice_id}")
    assert unchanged.status_code == 200
    assert unchanged.json()["lifecycle_status"] == "draft"
    assert unchanged.json()["number"] is None
    assert unchanged.json()["version"] == 1

    invoice_row = db_session.scalar(select(Invoice).where(Invoice.id == UUID(invoice_id)))
    assert invoice_row is not None
    assert invoice_row.lifecycle_status is LifecycleStatus.DRAFT
    assert invoice_row.number is None
    assert db_session.scalar(select(func.count()).select_from(StockMovement)) == 0
    assert db_session.scalar(select(func.count()).select_from(StockBalance)) == 0
    assert db_session.scalar(select(func.count()).select_from(AccountingEntry)) == 0
    assert db_session.scalar(select(func.count()).select_from(NumberSequence)) == 0
    assert (
        _balances(
            client,
            warehouse_id=str(warehouse["id"]),
            item_id=str(item["id"]),
        )
        == []
    )


def test_issue_invoice_with_partial_stock_does_not_apply_atomic_lines(
    client: TestClient,
    db_session: Session,
) -> None:
    warehouse = _create_warehouse(client)
    item = _create_item(client)
    contact = _create_contact(client)
    incoming = _register_movement(
        client,
        item_id=str(item["id"]),
        warehouse_id=str(warehouse["id"]),
        movement_type="IN",
        quantity="5.0000",
    )
    assert incoming.status_code == 201, incoming.text

    draft = _create_draft_invoice(
        client,
        contact_id=str(contact["id"]),
        item_id=str(item["id"]),
        quantities=["4.0000", "3.0000"],
    )
    assert draft.status_code == 201, draft.text

    response = client.post(f"/api/v1/invoices/{draft.json()['id']}/issue")

    assert response.status_code == 409
    assert "Stock insuficiente" in response.json()["detail"]
    assert _money(
        _balances(
            client,
            warehouse_id=str(warehouse["id"]),
            item_id=str(item["id"]),
        )[0]["quantity"]
    ) == Decimal("5.00")
    assert (
        db_session.scalar(
            select(func.count())
            .select_from(StockMovement)
            .where(StockMovement.movement_type == StockMovementType.OUT)
        )
        == 0
    )


def test_warehouse_code_is_unique_and_delete_deactivates(client: TestClient) -> None:
    warehouse = _create_warehouse(client)
    duplicate = client.post(
        "/api/v1/warehouses",
        json={"name": "Otra bodega", "code": warehouse["code"]},
    )
    assert duplicate.status_code == 409

    deleted = client.delete(f"/api/v1/warehouses/{warehouse['id']}")
    assert deleted.status_code == 204

    fetched = client.get(f"/api/v1/warehouses/{warehouse['id']}")
    assert fetched.status_code == 200
    assert fetched.json()["is_active"] is False
