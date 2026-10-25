"""Tests de reportes financieros (Estado de Resultados y Balance General)."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from typing import Any
from uuid import uuid4

from fastapi.testclient import TestClient

TWOPLACES = Decimal("0.01")


def _money(value: object) -> Decimal:
    return Decimal(str(value)).quantize(TWOPLACES)


def _setup_invoice_for_report(
    client: TestClient,
    *,
    unit_cost: str | None = None,
) -> dict[str, Any]:
    """Crea contacto, ítem, bodega con stock y factura emitida con pago.

    ``unit_cost`` valoriza el stock inicial para que la venta genere el
    asiento de costo de ventas (PUC 6135) además del asiento de ingreso.
    """
    contact = client.post(
        "/api/v1/contacts",
        json={"name": "Cliente Reporte", "email": "reporte@example.com"},
    )
    assert contact.status_code == 201, contact.text
    contact = contact.json()

    tax = client.post(
        "/api/v1/taxes",
        json={"name": "IVA 19 %", "rate": "19.0000"},
    )
    assert tax.status_code == 201, tax.text
    tax = tax.json()

    item = client.post(
        "/api/v1/items",
        json={
            "name": "Producto Reporte",
            "description": "Producto Reporte",
            "unit_price": "100.00",
            "tax_id": str(tax["id"]),
        },
    )
    assert item.status_code == 201, item.text
    item = item.json()

    warehouse = client.post(
        "/api/v1/warehouses",
        json={"name": "Bodega Reporte", "code": "REPORTE"},
    )
    assert warehouse.status_code == 201, warehouse.text
    warehouse = warehouse.json()

    movement_payload: dict[str, str] = {
        "item_id": str(item["id"]),
        "warehouse_id": warehouse["id"],
        "movement_type": "IN",
        "quantity": "20",
    }
    if unit_cost is not None:
        movement_payload["unit_cost"] = unit_cost
    client.post("/api/v1/inventory/movements", json=movement_payload)

    today = date.today().isoformat()
    due_date = (date.today() + timedelta(days=30)).isoformat()

    invoice = client.post(
        "/api/v1/invoices",
        json={
            "contact_id": str(contact["id"]),
            "issue_date": today,
            "due_date": due_date,
            "currency": "COP",
            "lines": [
                {
                    "item_id": str(item["id"]),
                    "quantity": "2",
                    "unit_price": "100.00",
                    "discount_percent": "0",
                    "tax_rate": "19",
                }
            ],
        },
        headers={"Idempotency-Key": str(uuid4())},
    )
    assert invoice.status_code == 201, invoice.text
    invoice = invoice.json()

    issued = client.post(f"/api/v1/invoices/{invoice['id']}/issue")
    assert issued.status_code == 200, issued.text

    # 2 unidades vendidas; el COGS es 2 * unit_cost cuando el stock está
    # valorizado.
    cogs = Decimal(unit_cost) * Decimal("2") if unit_cost is not None else Decimal("0.00")

    return {
        "invoice_id": str(invoice["id"]),
        "invoice_number": issued.json()["number"],
        "total": Decimal("238.00"),  # 2 * 100 + 19% IVA = 238.00
        "subtotal": Decimal("200.00"),
        "tax_total": Decimal("38.00"),
        "cogs": cogs,
    }


def test_income_statement_shows_revenue(client: TestClient) -> None:
    data = _setup_invoice_for_report(client)

    response = client.get("/api/v1/reports/income-statement")
    assert response.status_code == 200, response.text
    report = response.json()

    # Debería haber una cuenta de ingresos con saldo positivo
    income_accounts = report["income_accounts"]
    revenue_found = False
    for acct in income_accounts:
        if acct["code"] == "413505":  # Comercio al por mayor y al por menor
            assert _money(acct["balance"]) == data["subtotal"]
            revenue_found = True
    assert revenue_found, f"No se encontró la cuenta de ingresos en {income_accounts}"

    # Debería haber una cuenta de IVA generado (pasivo, no gasto)
    expense_accounts = report["expense_accounts"]
    # No debería haber gastos en este escenario
    assert len(expense_accounts) == 0 or all(_money(a["balance"]) == 0 for a in expense_accounts)

    assert _money(report["total_income"]) == data["subtotal"]
    assert _money(report["net_income"]) == data["subtotal"]


def test_income_statement_subtracts_cogs_and_balance_balances(
    client: TestClient,
) -> None:
    """El costo de ventas (PUC 6135) se descuenta de la utilidad neta.

    Regresión: antes las cuentas COSTO quedaban fuera del Estado de
    Resultados, la utilidad neta quedaba inflada por el COGS y el Balance
    General descuadraba exactamente por ese monto.
    """
    data = _setup_invoice_for_report(client, unit_cost="40.00")

    income = client.get("/api/v1/reports/income-statement")
    assert income.status_code == 200, income.text
    report = income.json()

    # 2 unidades vendidas * 40.00 de costo promedio = 80.00 en la 6135.
    cogs_rows = [a for a in report["expense_accounts"] if a["code"] == "6135"]
    assert len(cogs_rows) == 1, f"No se encontró la 6135 en {report['expense_accounts']}"
    assert _money(cogs_rows[0]["balance"]) == data["cogs"]

    # La utilidad neta descuenta gastos y costos de los ingresos.
    assert _money(report["total_expenses"]) == data["cogs"]
    assert _money(report["net_income"]) == data["subtotal"] - data["cogs"]

    balance = client.get("/api/v1/reports/balance-sheet")
    assert balance.status_code == 200, balance.text
    sheet = balance.json()
    assert sheet["balanced"] is True
    assert _money(sheet["total_assets"]) == _money(sheet["total_liabilities"]) + _money(
        sheet["total_equity"]
    )


def test_balance_sheet_balances(client: TestClient) -> None:
    data = _setup_invoice_for_report(client)

    response = client.get("/api/v1/reports/balance-sheet")
    assert response.status_code == 200, response.text
    report = response.json()

    assert report["balanced"] is True
    assert _money(report["total_assets"]) == _money(report["total_liabilities"]) + _money(
        report["total_equity"]
    )

    # Debería haber una cuenta de Cuentas por Cobrar con saldo positivo
    asset_found = False
    for acct in report["asset_accounts"]:
        if acct["code"] == "130505":  # Clientes nacionales
            assert _money(acct["balance"]) == data["total"]
            asset_found = True
    assert asset_found, f"No se encontró Cuentas por Cobrar en {report['asset_accounts']}"


def test_balance_sheet_reclassifies_debit_balance_liabilities(
    client: TestClient,
) -> None:
    """Un pasivo con saldo débito se presenta como activo, no como pasivo negativo.

    Regresión H-1 de la auditoría contable: la 240802 (IVA descontable a
    favor) debe reclasificarse al activo con signo positivo en lugar de
    desinflar el total de pasivos, sin romper A = P + Pt.
    """
    supplier = client.post(
        "/api/v1/contacts",
        json={"name": "Proveedor IVA", "email": "iva-reporte@example.com", "type": "supplier"},
    )
    assert supplier.status_code == 201, supplier.text
    item = client.post(
        "/api/v1/items",
        json={"name": "Producto IVA", "description": "Producto IVA", "unit_price": "100.00"},
    )
    assert item.status_code == 201, item.text

    warehouse = client.post(
        "/api/v1/warehouses",
        json={"name": "Bodega IVA", "code": "IVA-BS"},
    )
    assert warehouse.status_code == 201, warehouse.text

    purchase = client.post(
        "/api/v1/purchases",
        json={
            "supplier_id": supplier.json()["id"],
            "issue_date": date.today().isoformat(),
            "due_date": (date.today() + timedelta(days=30)).isoformat(),
            "lines": [
                {
                    "item_id": item.json()["id"],
                    "description": "Producto IVA",
                    "quantity": "1",
                    "unit_cost": "100.00",
                    "tax_rate": "19",
                }
            ],
        },
        headers={"Idempotency-Key": str(uuid4())},
    )
    assert purchase.status_code == 201, purchase.text
    issued = client.post(f"/api/v1/purchases/{purchase.json()['id']}/issue")
    assert issued.status_code == 200, issued.text
    # La compra quedó impaga: 240802 tiene saldo débito de 19.00.

    response = client.get("/api/v1/reports/balance-sheet")
    assert response.status_code == 200, response.text
    sheet = response.json()

    asset_balances = {a["code"]: _money(a["balance"]) for a in sheet["asset_accounts"]}
    liability_balances = {a["code"]: _money(a["balance"]) for a in sheet["liability_accounts"]}

    # El IVA descontable a favor se presenta del lado del activo, positivo.
    assert asset_balances.get("240802") == Decimal("19.00")
    assert "240802" not in liability_balances

    # Y el balance sigue cuadrando.
    assert sheet["balanced"] is True
    assert _money(sheet["total_assets"]) == _money(sheet["total_liabilities"]) + _money(
        sheet["total_equity"]
    )


def test_income_statement_requires_authentication(
    anonymous_client: TestClient,
) -> None:
    assert anonymous_client.get("/api/v1/reports/income-statement").status_code == 401
    assert anonymous_client.get("/api/v1/reports/balance-sheet").status_code == 401
