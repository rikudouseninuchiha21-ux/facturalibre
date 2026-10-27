#!/usr/bin/env python3
# ruff: noqa: E402
"""Puebla la base de datos de desarrollo con datos de demostración.

El script reutiliza los servicios y repositorios de la aplicación para que las
facturas, pagos, gastos, movimientos bancarios y depreciaciones generen sus
respectivos asientos contables y movimientos de inventario.

Uso:
    python scripts/seed_demo_data.py --reset

Solo se ejecuta cuando ``ENVIRONMENT=development``. ``--reset`` elimina los
datos de negocio existentes, pero conserva el catálogo PUC y la tabla de
migraciones de Alembic.
"""

from __future__ import annotations

import argparse
import calendar
import sys
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any, TypedDict

# El archivo se ejecuta directamente desde backend/; el ajuste de sys.path debe
# ocurrir antes de importar el paquete app.
BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from sqlalchemy import Select, func, inspect, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from app.application.accounting.service import AccountingService
from app.application.auth.service import AuthService
from app.application.contact_schemas import ContactCreate
from app.application.dian.nit import compute_dv
from app.application.expense_schemas import ExpenseCreate
from app.application.expense_service import ExpenseService
from app.application.fixed_asset_schemas import FixedAssetCreate
from app.application.fixed_asset_service import FixedAssetService
from app.application.inventory.service import InventoryService
from app.application.invoice_schemas import InvoiceCreate, InvoiceLineCreate
from app.application.invoice_service import apply_invoice_issue_effects, create_invoice_draft
from app.application.item_schemas import ItemCreate
from app.application.payment_service import PaymentService
from app.application.purchase_schemas import PurchaseCreate, PurchaseLineCreate
from app.application.tax_schemas import TaxCreate
from app.application.treasury_schemas import BankAccountCreate, BankTransactionCreate
from app.application.treasury_service import TreasuryService
from app.application.user_schemas import UserCreate
from app.core.config import get_settings
from app.domain.calculations import LineAmounts, calculate_invoice_totals, round_money
from app.domain.company_setting_repository import CompanySettingRepository
from app.domain.contact_repository import ContactRepository
from app.domain.cost_center_repository import CostCenterRepository
from app.domain.invoice_repository import InvoiceRepository
from app.domain.item_repository import ItemRepository
from app.domain.models.accounting import AccountingEntry, AccountingEntryLine
from app.domain.models.auth import User, UserRole
from app.domain.models.bank import (
    BankAccount,
    BankAccountType,
    BankTransaction,
    BankTransactionType,
)
from app.domain.models.budgeting import CostCenter
from app.domain.models.company_setting import CompanySetting
from app.domain.models.contact import Contact, ContactStatus, ContactType
from app.domain.models.expense import Expense
from app.domain.models.fixed_asset import DepreciationEntry, FixedAsset
from app.domain.models.invoice import Invoice, LifecycleStatus
from app.domain.models.item import Item
from app.domain.models.payment import Payment
from app.domain.models.purchase import PurchaseInvoice
from app.domain.models.stock import StockBalance, StockMovementType
from app.domain.models.tax import Tax
from app.domain.models.warehouse import Warehouse
from app.domain.purchase_repository import NewPurchaseLine, PurchaseRepository
from app.domain.tax_repository import TaxRepository
from app.domain.warehouse_repository import WarehouseRepository
from app.infrastructure.database import SessionLocal
from app.infrastructure.transactions import operation_transaction

PASSWORD = "password123"
ZERO = Decimal("0.00")
HUNDRED = Decimal("100")
TWOPLACES = Decimal("0.01")
CURRENT_MONTH_OFFSETS = (-5, -4, -3, -2, -1, 0)
MONTH_COUNTS = (3, 3, 3, 4, 4, 3)
INVOICE_DAYS = (5, 14, 23, 28)
PAYMENT_PATTERN = {
    -5: ("paid", "paid", "paid"),
    -4: ("paid", "paid", "paid"),
    -3: ("paid", "paid", "paid"),
    -2: ("paid", "paid", "partial", "unpaid"),
    -1: ("paid", "partial", "partial", "unpaid"),
    0: ("paid", "partial", "unpaid"),
}


class ItemSeedData(TypedDict):
    """Atributos de un ítem del catálogo de demostración."""

    name: str
    description: str
    unit_price: Decimal
    cost: Decimal
    tax: str
    price_includes_tax: bool


# Los precios incluyen o no IVA según el catálogo. El costo no vive en el
# modelo Item; se conserva en este mapa para cargar el inventario inicial con
# costo promedio ponderado realista.
ITEM_DATA: tuple[ItemSeedData, ...] = (
    {
        "name": "Computador portátil Lenovo ThinkPad E14",
        "description": 'Portátil empresarial 14", 16 GB RAM, 512 GB SSD',
        "unit_price": Decimal("3499000.00"),
        "cost": Decimal("2450000.00"),
        "tax": "IVA 19%",
        "price_includes_tax": True,
    },
    {
        "name": 'Monitor LG UltraWide 27"',
        "description": 'Monitor IPS 27" QHD con conexión USB-C',
        "unit_price": Decimal("899000.00"),
        "cost": Decimal("610000.00"),
        "tax": "IVA 19%",
        "price_includes_tax": True,
    },
    {
        "name": "Silla ergonómica Mesh",
        "description": "Silla de oficina con soporte lumbar ajustable",
        "unit_price": Decimal("549900.00"),
        "cost": Decimal("320000.00"),
        "tax": "IVA 19%",
        "price_includes_tax": False,
    },
    {
        "name": "Impresora multifuncional HP",
        "description": "Impresora láser multifuncional para oficina",
        "unit_price": Decimal("699000.00"),
        "cost": Decimal("430000.00"),
        "tax": "IVA 5%",
        "price_includes_tax": False,
    },
    {
        "name": "Resma de papel bond carta",
        "description": "Resma de 500 hojas, papel bond 75 g",
        "unit_price": Decimal("21900.00"),
        "cost": Decimal("13500.00"),
        "tax": "Excluido",
        "price_includes_tax": False,
    },
)

CUSTOMERS = (
    {
        "name": "Distribuidora Andina S.A.S.",
        "email": "compras@distribuidoraandina.com",
        "tax_id": "900123456-7",
    },
    {
        "name": "Almacenes La Estrella Ltda.",
        "email": "pagos@almaceneslaestrella.com",
        "tax_id": "860987654-1",
    },
    {
        "name": "Clínica San Rafael",
        "email": "administracion@clinicasanrafael.com",
        "tax_id": "830456789-2",
    },
)

SUPPLIERS = (
    {
        "name": "Tecnología Global S.A.S.",
        "email": "ventas@tecnologiaglobal.com",
        "tax_id": "901234567-8",
    },
    {
        "name": "Suministros del Norte Ltda.",
        "email": "pedidos@suministrosdelnorte.com",
        "tax_id": "890765432-1",
    },
)

EXPENSES = (
    ("Arriendo oficina administrativa", Decimal("1850000.00")),
    ("Servicios públicos (energía y agua)", Decimal("620000.00")),
    ("Internet y telefonía corporativa", Decimal("289000.00")),
    ("Papelería y elementos de aseo", Decimal("175000.00")),
    ("Mantenimiento de equipos de cómputo", Decimal("450000.00")),
)

# Centros de costo base de la demostración. Se crean solo si no existen.
COST_CENTERS = (
    {"code": "CC-VEN", "name": "Ventas", "description": "Área comercial y de ventas"},
    {"code": "CC-ADM", "name": "Administración", "description": "Área administrativa"},
    {"code": "CC-PRO", "name": "Producción", "description": "Área de producción y operaciones"},
)


def _shift_month(year: int, month: int, offset: int) -> tuple[int, int]:
    """Desplaza un mes de calendario preservando el año."""
    index = (year * 12) + (month - 1) + offset
    return index // 12, (index % 12) + 1


def _month_date(offset: int, day: int, *, today: date) -> date:
    """Devuelve una fecha del mes relativo, nunca posterior a hoy."""
    year, month = _shift_month(today.year, today.month, offset)
    last_day = calendar.monthrange(year, month)[1]
    candidate = date(year, month, min(day, last_day))
    return min(candidate, today)


def _clamp_payment_date(issue_date: date, days: int, *, today: date) -> date:
    """Calcula una fecha de pago posterior a la emisión y no futura."""
    return min(issue_date + timedelta(days=days), today)


def _money(value: Decimal) -> str:
    """Formatea un importe para el resumen de consola."""
    return f"${value:,.2f}"


def _count(db: Session, model: type[object]) -> int:
    """Cuenta las filas de un modelo."""
    value = db.scalar(select(func.count()).select_from(model))
    return int(value or 0)


def _sum_money(db: Session, expression: Select[Any]) -> Decimal:
    """Normaliza un agregado monetario de SQLAlchemy a Decimal."""
    value = db.scalar(expression)
    if value is None:
        return ZERO
    return round_money(Decimal(str(value)))


def _reset_database(db: Session) -> None:
    """Elimina datos de negocio preservando PUC y el estado de Alembic."""
    inspector = inspect(db.get_bind())
    tables = inspector.get_table_names()
    preserve = {"alembic_version", "accounting_accounts"}
    to_truncate = sorted(set(tables) - preserve)
    if not to_truncate:
        return

    preparer = db.get_bind().dialect.identifier_preparer
    quoted_tables = ", ".join(preparer.quote(table) for table in to_truncate)
    db.execute(text(f"TRUNCATE TABLE {quoted_tables} RESTART IDENTITY CASCADE"))
    db.commit()
    print(f"Limpieza: {len(to_truncate)} tablas truncadas (PUC preservado).")


def _has_existing_data(db: Session) -> bool:
    """Indica si ya hay datos que harían ambiguo un nuevo seed."""
    for model in (
        User,
        Contact,
        Item,
        Tax,
        Warehouse,
        Invoice,
        PurchaseInvoice,
        Expense,
        BankAccount,
        FixedAsset,
    ):
        if _count(db, model) > 0:
            return True
    return False


def _seed_company(db: Session) -> CompanySetting:
    """Crea la configuración de la empresa si todavía no existe.

    Incluye los datos DIAN de demo (NIT sin puntos, DV, resolución de
    facturación y códigos DANE) para que las facturas del seeder puedan
    generar XML/PDF sin 422. El ``dian_software_pin`` queda vacío: los
    CUFE generados son de prueba (dian_status=GENERADO_SIN_PIN).
    """
    repository = CompanySettingRepository(db)
    with operation_transaction(db):
        company = repository.get()
        if company is None:
            company = repository.create(
                name="Nexus ERP S.A.S.",
                tax_id="901555123",
                address="Calle 100 # 15-20, Bogotá D.C., Colombia",
                phone="+57 601 555 0123",
                email="contacto@nexus.com",
                logo_url=None,
            )
            company.dv = "4"
            company.person_type = "JURIDICA"
            company.tax_regime = "RESPONSABLE_IVA"
            company.fiscal_responsibility = "O-13"
            company.dian_municipality_code = "11001"
            company.dian_department_code = "11"
            company.dian_resolution_number = "18764000000001"
            company.dian_resolution_prefix = "FE"
            company.dian_resolution_range_from = 1
            company.dian_resolution_range_to = 50_000
            company.dian_resolution_valid_from = date(2026, 1, 1)
            company.dian_resolution_valid_to = date(2027, 12, 31)
            company.dian_software_id = "NEXUS-ERP-DEMO"
    return company


def _seed_users(db: Session) -> list[User]:
    """Crea los tres usuarios de demostración con roles diferenciados."""
    service = AuthService(db)
    users = [
        ("admin@nexus.com", "Administrador Nexus", UserRole.ADMIN),
        ("contador@nexus.com", "Contador Nexus", UserRole.ACCOUNTANT),
        ("cajero@nexus.com", "Cajero Nexus", UserRole.CASHIER),
    ]
    created: list[User] = []
    for email, full_name, role in users:
        created.append(
            service.create_user(
                UserCreate(
                    email=email,
                    password=PASSWORD,
                    full_name=full_name,
                    role=role,
                )
            )
        )
    return created


def _seed_taxes(db: Session) -> dict[str, Tax]:
    """Crea el catálogo mínimo de impuestos."""
    repository = TaxRepository(db)
    payloads = (
        TaxCreate(name="IVA 19%", rate=Decimal("19.0000")),
        TaxCreate(name="IVA 5%", rate=Decimal("5.0000")),
        TaxCreate(name="Excluido", rate=Decimal("0.0000")),
    )
    return {payload.name: repository.create(payload.model_dump()) for payload in payloads}


def _seed_contacts(db: Session) -> tuple[list[Contact], list[Contact]]:
    """Crea tres clientes y dos proveedores con datos fiscales DIAN.

    El NIT se separa del DV cuando viene como "900123456-7"; si no trae DV
    se calcula con el algoritmo módulo 11. Así las facturas del seeder
    pasan la validación de datos del generador DIAN.
    """

    def _create(data: dict[str, str], contact_type: ContactType) -> Contact:
        nit, _, dv = data["tax_id"].partition("-")
        return repository.create(
            ContactCreate(
                name=data["name"],
                email=data["email"],
                tax_id=nit,
                type=contact_type,
                status=ContactStatus.CUSTOMER,
                address=f"Calle 100 # 8-{(int(nit[-2:]) % 90) + 10}, Bogotá D.C.",
                dv=dv or compute_dv(nit),
                person_type="JURIDICA",
                tax_regime="RESPONSABLE_IVA",
                dian_municipality_code="11001",
                dian_department_code="11",
            ).model_dump()
        )

    repository = ContactRepository(db)
    customers = [_create(data, ContactType.CUSTOMER) for data in CUSTOMERS]
    suppliers = [_create(data, ContactType.SUPPLIER) for data in SUPPLIERS]
    return customers, suppliers


def _seed_items(db: Session, taxes: dict[str, Tax]) -> list[Item]:
    """Crea cinco ítems con impuesto y precio con/sin IVA."""
    repository = ItemRepository(db)
    return [
        repository.create(
            ItemCreate(
                name=data["name"],
                description=data["description"],
                unit_price=data["unit_price"],
                tax_id=taxes[data["tax"]].id,
                price_includes_tax=data["price_includes_tax"],
            ).model_dump()
        )
        for data in ITEM_DATA
    ]


def _seed_warehouse(db: Session) -> Warehouse:
    """Crea la bodega principal usada por inventario y facturación."""
    repository = WarehouseRepository(db)
    return repository.create({"name": "Bodega Principal", "code": "PRINCIPAL", "is_active": True})


def _seed_cost_centers(db: Session) -> list[CostCenter]:
    """Crea los tres centros de costo base si no existen (idempotente)."""
    repository = CostCenterRepository(db)
    centers: list[CostCenter] = []
    for data in COST_CENTERS:
        center = repository.get_by_code(data["code"])
        if center is None:
            center = repository.create(dict(data))
        centers.append(center)
    db.commit()
    return centers


def _purchase_line(
    *,
    item: Item,
    cost: Decimal,
    tax_rate: Decimal,
    quantity: Decimal,
) -> NewPurchaseLine:
    """Calcula una línea de compra con la misma regla que la API."""
    subtotal = round_money(quantity * cost)
    tax = round_money(subtotal * tax_rate / HUNDRED)
    return NewPurchaseLine(
        item_id=item.id,
        description=item.name,
        quantity=quantity,
        unit_cost=cost,
        tax_rate=tax_rate,
        line_subtotal=subtotal,
        line_tax=tax,
        line_total=round_money(subtotal + tax),
    )


def _seed_initial_inventory(
    db: Session,
    *,
    items: list[Item],
    suppliers: list[Contact],
    taxes: dict[str, Tax],
    warehouse: Warehouse,
    purchase_date: date,
) -> tuple[list[PurchaseInvoice], int]:
    """Carga 100 unidades por ítem mediante facturas de compra emitidas.

    Usar el flujo de compras (en lugar de un movimiento de inventario aislado)
    deja el stock y la cuenta de inventario respaldados por el mismo asiento
    contable.
    """
    repository = PurchaseRepository(db)
    inventory = InventoryService(db)
    accounting = AccountingService(db)
    purchase_groups = ((suppliers[0], (0, 1, 2)), (suppliers[1], (3, 4)))
    purchases: list[PurchaseInvoice] = []
    units = 0

    for supplier, item_indexes in purchase_groups:
        lines = [
            _purchase_line(
                item=items[index],
                cost=ITEM_DATA[index]["cost"],
                tax_rate=taxes[ITEM_DATA[index]["tax"]].rate,
                quantity=HUNDRED,
            )
            for index in item_indexes
        ]
        totals = calculate_invoice_totals(
            LineAmounts(
                subtotal=line.line_subtotal,
                tax=line.line_tax,
                total=line.line_total,
            )
            for line in lines
        )
        payload = PurchaseCreate(
            supplier_id=supplier.id,
            issue_date=purchase_date,
            due_date=purchase_date + timedelta(days=30),
            lines=[
                PurchaseLineCreate(
                    item_id=line.item_id,
                    description=line.description,
                    quantity=line.quantity,
                    unit_cost=line.unit_cost,
                    tax_rate=line.tax_rate,
                )
                for line in lines
            ],
        )

        with operation_transaction(db):
            purchase = repository.create_draft(
                supplier_id=payload.supplier_id,
                issue_date=payload.issue_date,
                due_date=payload.due_date,
                lines=lines,
                subtotal=totals.subtotal,
                tax_total=totals.tax_total,
                total=totals.total,
            )
            purchase = repository.issue(purchase.id)
            for line in purchase.lines:
                if line.item_id is None:
                    continue
                inventory.register_movement(
                    item_id=line.item_id,
                    warehouse_id=warehouse.id,
                    movement_type=StockMovementType.IN,
                    quantity=line.quantity,
                    unit_cost=line.unit_cost,
                    reference=purchase.number or str(purchase.id),
                )
                units += int(line.quantity)
            accounting.record_purchase_issued(purchase)
        purchases.append(purchase)

    return purchases, units


def _invoice_line_specs(index: int) -> list[tuple[int, Decimal]]:
    """Genera una mezcla determinista de una a tres líneas por factura."""
    first = index % 5
    quantity = Decimal("2") if index % 3 == 0 else Decimal("1")
    specs: list[tuple[int, Decimal]] = [(first, quantity)]

    if index % 2 == 0:
        second = (index + 2) % 5
        if second != first:
            specs.append((second, Decimal("1")))

    if index % 5 == 0:
        third = (index + 4) % 5
        if all(item_index != third for item_index, _ in specs):
            specs.append((third, Decimal("1")))

    return specs


def _seed_sales(
    db: Session,
    *,
    customers: list[Contact],
    items: list[Item],
    today: date,
) -> tuple[list[Invoice], list[Payment], list[Expense]]:
    """Crea 20 facturas de venta, sus pagos y cinco gastos operativos."""
    invoices: list[Invoice] = []
    payments: list[Payment] = []
    expenses: list[Expense] = []
    invoice_repository = InvoiceRepository(db)
    payment_service = PaymentService(db)
    expense_service = ExpenseService(db)
    invoice_index = 0

    for offset, count in zip(CURRENT_MONTH_OFFSETS, MONTH_COUNTS, strict=True):
        statuses = PAYMENT_PATTERN[offset]
        for position in range(count):
            issue_day = INVOICE_DAYS[position % len(INVOICE_DAYS)]
            issue_date = _month_date(offset, issue_day, today=today)
            specs = _invoice_line_specs(invoice_index)
            discount = Decimal("5.00") if invoice_index % 4 == 0 else ZERO
            payload = InvoiceCreate(
                contact_id=customers[invoice_index % len(customers)].id,
                issue_date=issue_date,
                due_date=issue_date + timedelta(days=30),
                payment_mean_code="10",
                lines=[
                    InvoiceLineCreate(
                        item_id=items[item_index].id,
                        quantity=quantity,
                        unit_price=items[item_index].unit_price,
                        discount_percent=discount,
                    )
                    for item_index, quantity in specs
                ],
            )

            with operation_transaction(db):
                invoice = create_invoice_draft(db, payload)
                invoice = invoice_repository.issue(invoice.id)
                apply_invoice_issue_effects(db, invoice)

            status = statuses[position]
            if status != "unpaid":
                if status == "paid":
                    amount = round_money(invoice.total)
                    payment_days = 12
                else:
                    amount = round_money(invoice.total * Decimal("0.40"))
                    payment_days = 6
                payment_date = _clamp_payment_date(
                    invoice.issue_date or issue_date,
                    payment_days,
                    today=today,
                )
                with operation_transaction(db):
                    payment = payment_service.register_payment(
                        invoice=invoice,
                        amount=amount,
                        payment_date=payment_date,
                        method="efectivo",
                        reference=f"Recaudo factura {invoice.number}",
                    )
                payments.append(payment)

            invoices.append(invoice)
            invoice_index += 1

    for index, (concept, amount) in enumerate(EXPENSES):
        offset = -4 + index
        expense_date = _month_date(offset, 3 + (index * 2), today=today)
        with operation_transaction(db):
            expense = expense_service.create_expense(
                **ExpenseCreate(
                    date=expense_date,
                    concept=concept,
                    amount=amount,
                    payment_method="efectivo",
                    reference=f"Gasto operativo {expense_date:%Y-%m}",
                ).model_dump()
            )
        expenses.append(expense)

    return invoices, payments, expenses


def _seed_bank(
    db: Session,
    *,
    today: date,
    asset_purchase_date: date,
    cash_receipts: Decimal,
    cash_expenses: Decimal,
    asset_cost: Decimal,
) -> tuple[BankAccount, list[BankTransaction]]:
    """Crea la cuenta bancaria y registra depósitos y retiros."""
    service = TreasuryService(db)
    with operation_transaction(db):
        account = service.create_account(
            BankAccountCreate(
                name="Cuenta de ahorros Bancolombia",
                bank_name="Bancolombia",
                account_number="123-456789-01",
                account_type=BankAccountType.SAVINGS,
                currency="COP",
                accounting_account_code="11100501",
            )
        )

    cash_available = cash_receipts - cash_expenses
    deposit_from_cash = min(
        Decimal("8000000.00"),
        max(cash_available - Decimal("1000000.00"), ZERO),
    )
    second_deposit = min(
        Decimal("1500000.00"),
        max(cash_available - deposit_from_cash - Decimal("500000.00"), ZERO),
    )
    financing_needed = max(
        asset_cost + Decimal("500000.00") - deposit_from_cash - second_deposit,
        ZERO,
    )
    transactions: list[BankTransaction] = []

    def add_transaction(payload: BankTransactionCreate) -> None:
        with operation_transaction(db):
            transaction = service.create_transaction(account.id, payload)
        transactions.append(transaction)

    if deposit_from_cash > ZERO:
        add_transaction(
            BankTransactionCreate(
                transaction_type=BankTransactionType.DEPOSIT,
                date=max(asset_purchase_date - timedelta(days=20), today - timedelta(days=180)),
                amount=deposit_from_cash,
                description="Consignación de recaudos en efectivo",
                reference="CONS-001",
                counterpart_account_code="110505",
            )
        )
    if second_deposit > ZERO:
        add_transaction(
            BankTransactionCreate(
                transaction_type=BankTransactionType.DEPOSIT,
                date=max(asset_purchase_date - timedelta(days=12), today - timedelta(days=180)),
                amount=second_deposit,
                description="Consignación adicional de caja",
                reference="CONS-002",
                counterpart_account_code="110505",
            )
        )
    if financing_needed > ZERO:
        add_transaction(
            BankTransactionCreate(
                transaction_type=BankTransactionType.DEPOSIT,
                date=max(asset_purchase_date - timedelta(days=10), today - timedelta(days=180)),
                amount=financing_needed,
                description="Financiación de proveedor para compra de activo",
                reference="FIN-001",
                counterpart_account_code="220505",
            )
        )

    add_transaction(
        BankTransactionCreate(
            transaction_type=BankTransactionType.WITHDRAWAL,
            date=asset_purchase_date,
            amount=asset_cost,
            description='Compra de Computador MacBook Pro 14"',
            reference="AF-001",
            counterpart_account_code="15",
        )
    )
    add_transaction(
        BankTransactionCreate(
            transaction_type=BankTransactionType.WITHDRAWAL,
            date=min(asset_purchase_date + timedelta(days=2), today),
            amount=Decimal("400000.00"),
            description="Retiro para caja menor",
            reference="RET-001",
            counterpart_account_code="110505",
        )
    )
    return account, transactions


def _seed_fixed_asset(
    db: Session,
    *,
    purchase_date: date,
    today: date,
) -> tuple[FixedAsset, int]:
    """Crea el activo fijo y lo deprecia durante los dos últimos meses completos."""
    service = FixedAssetService(db)
    payload = FixedAssetCreate(
        code="AF-001",
        name='Computador MacBook Pro 14"',
        purchase_date=purchase_date,
        initial_cost=Decimal("6500000.00"),
        salvage_value=Decimal("500000.00"),
        useful_life_months=36,
    )
    with operation_transaction(db):
        asset = service.create_asset(**payload.model_dump())

    depreciated = 0
    for offset in (-2, -1):
        year, month = _shift_month(today.year, today.month, offset)
        with operation_transaction(db):
            service.depreciate_asset(asset_id=asset.id, year=year, month=month)
        depreciated += 1

    return asset, depreciated


def _print_summary(db: Session, *, reset: bool) -> None:
    """Imprime cantidades, totales y una validación contable básica."""
    sales_total = _sum_money(
        db,
        select(func.coalesce(func.sum(Invoice.total), ZERO)).where(
            Invoice.lifecycle_status == LifecycleStatus.ISSUED
        ),
    )
    pending_balance = _sum_money(
        db,
        select(func.coalesce(func.sum(Invoice.balance), ZERO)).where(
            Invoice.lifecycle_status == LifecycleStatus.ISSUED
        ),
    )
    stock_total = _sum_money(
        db,
        select(func.coalesce(func.sum(StockBalance.quantity), ZERO)),
    )
    debits, credits = db.execute(
        select(
            func.coalesce(func.sum(AccountingEntryLine.debit), ZERO),
            func.coalesce(func.sum(AccountingEntryLine.credit), ZERO),
        )
    ).one()
    debits = round_money(Decimal(str(debits)))
    credits = round_money(Decimal(str(credits)))
    bank_transactions = _count(db, BankTransaction)
    depreciation_entries = _count(db, DepreciationEntry)

    print()
    print("=" * 66)
    print("RESUMEN DEL SEED DE DEMOSTRACIÓN")
    print("=" * 66)
    print(f"Limpieza previa: {'sí' if reset else 'no'}")
    print()
    print(f"Usuarios:              {_count(db, User)}")
    print(f"Contactos:             {_count(db, Contact)} (3 clientes, 2 proveedores)")
    print(f"Impuestos:             {_count(db, Tax)}")
    print(f"Ítems:                 {_count(db, Item)}")
    print(f"Bodegas:               {_count(db, Warehouse)}")
    print(f"Centros de costo:      {_count(db, CostCenter)}")
    print("Stock inicial:         500 unidades (100 por ítem)")
    print(f"Stock actual:          {stock_total:,.2f} unidades")
    print(f"Facturas de compra:    {_count(db, PurchaseInvoice)}")
    print(f"Facturas de venta:     {_count(db, Invoice)}")
    print(f"Pagos de clientes:     {_count(db, Payment)}")
    print(f"Gastos operativos:     {_count(db, Expense)}")
    print(f"Cuentas bancarias:     {_count(db, BankAccount)}")
    print(f"Movimientos bancarios: {bank_transactions}")
    print(f"Activos fijos:         {_count(db, FixedAsset)}")
    print(f"Depreciaciones:        {depreciation_entries}")
    print(f"Asientos contables:    {_count(db, AccountingEntry)}")
    print(f"Líneas contables:      {_count(db, AccountingEntryLine)}")
    print()
    print(f"Facturación emitida:   {_money(sales_total)}")
    print(f"Cartera pendiente:     {_money(pending_balance)}")
    print(f"Débitos contables:     {_money(debits)}")
    print(f"Créditos contables:    {_money(credits)}")
    print(f"Partida doble:         {'OK' if debits == credits else 'DESCUADRADA'}")
    print()
    print("Acceso:")
    print("  admin@nexus.com     / password123  (ADMIN)")
    print("  contador@nexus.com  / password123  (ACCOUNTANT)")
    print("  cajero@nexus.com    / password123  (CASHIER)")
    print("=" * 66)


def main() -> None:
    """Punto de entrada del script."""
    parser = argparse.ArgumentParser(
        description="Puebla la base de datos de desarrollo con datos de demostración."
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Elimina los datos de negocio existentes antes de sembrar.",
    )
    args = parser.parse_args()

    settings = get_settings()
    environment = settings.environment.strip().lower()
    if environment not in {"development", "dev", "local"}:
        raise SystemExit(
            "Este script solo puede ejecutarse con ENVIRONMENT=development. "
            f"Entorno actual: {settings.environment!r}."
        )

    safe_url = make_url(settings.database_url).render_as_string(hide_password=True)
    print(f"Entorno: {settings.environment}")
    print(f"Base de datos: {safe_url}")

    with SessionLocal() as db:
        inspector = inspect(db.get_bind())
        if "accounting_accounts" not in inspector.get_table_names():
            raise SystemExit(
                "La base de datos no tiene el esquema migrado. "
                "Ejecuta 'alembic upgrade head' antes del seed."
            )

        if args.reset:
            _reset_database(db)
        elif _has_existing_data(db):
            raise SystemExit(
                "La base de datos ya contiene datos. "
                "Ejecuta el script con --reset para limpiar y volver a sembrar."
            )

        # Cierra cualquier transacción implícita abierta por las consultas de
        # verificación. Los catálogos confirman sus propios cambios.
        db.commit()

        _seed_company(db)
        _seed_users(db)
        taxes = _seed_taxes(db)
        customers, suppliers = _seed_contacts(db)
        items = _seed_items(db, taxes)
        warehouse = _seed_warehouse(db)
        _seed_cost_centers(db)
        # WarehouseRepository refresca la instancia después del commit; ese
        # refresh abre una transacción implícita que debe cerrarse antes de
        # comenzar las operaciones contables.
        db.commit()

        today = date.today()
        purchase_date = _month_date(-5, 1, today=today)
        _seed_initial_inventory(
            db,
            items=items,
            suppliers=suppliers,
            taxes=taxes,
            warehouse=warehouse,
            purchase_date=purchase_date,
        )

        invoices, payments, expenses = _seed_sales(
            db,
            customers=customers,
            items=items,
            today=today,
        )

        asset_purchase_date = _month_date(-3, 1, today=today)
        _seed_fixed_asset(db, purchase_date=asset_purchase_date, today=today)
        _seed_bank(
            db,
            today=today,
            asset_purchase_date=asset_purchase_date,
            cash_receipts=sum((payment.amount for payment in payments), ZERO),
            cash_expenses=sum((expense.amount for expense in expenses), ZERO),
            asset_cost=Decimal("6500000.00"),
        )

        _print_summary(db, reset=args.reset)


if __name__ == "__main__":
    main()
