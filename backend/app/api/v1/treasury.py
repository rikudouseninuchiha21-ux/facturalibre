"""Endpoints de bancos y tesorería: cuentas, movimientos y conciliación."""

from __future__ import annotations

from decimal import Decimal
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies.auth import get_current_user, require_role
from app.application.accounting.schemas import AccountingAccountRead
from app.application.treasury_schemas import (
    BankAccountCreate,
    BankAccountRead,
    BankAccountUpdate,
    BankTransactionCreate,
    BankTransactionRead,
    ReconcileRequest,
    TreasurySummary,
)
from app.application.treasury_service import TreasuryService
from app.domain.accounting_repository import AccountingRepository
from app.domain.bank_repository import (
    AccountBalanceSummary,
    BankAccountRepository,
    BankTransactionRepository,
)
from app.domain.exceptions import ResourceNotFoundError
from app.domain.models.auth import UserRole
from app.domain.models.bank import BankAccount
from app.infrastructure.database import get_db
from app.infrastructure.transactions import operation_transaction

router = APIRouter(
    prefix="/treasury",
    tags=["treasury"],
    dependencies=[
        Depends(get_current_user),
        Depends(require_role([UserRole.ADMIN, UserRole.ACCOUNTANT])),
    ],
)

DbSession = Annotated[Session, Depends(get_db)]


def get_bank_account_repository(db: DbSession) -> BankAccountRepository:
    """Construye el repositorio de cuentas bancarias."""
    return BankAccountRepository(db)


def get_bank_transaction_repository(db: DbSession) -> BankTransactionRepository:
    """Construye el repositorio de movimientos bancarios."""
    return BankTransactionRepository(db)


def get_treasury_service(db: DbSession) -> TreasuryService:
    """Construye el servicio de tesorería con la sesión de la petición."""
    return TreasuryService(db)


def get_accounting_repository(db: DbSession) -> AccountingRepository:
    """Construye el repositorio contable para el catálogo PUC."""
    return AccountingRepository(db)


BankAccountRepositoryDep = Annotated[BankAccountRepository, Depends(get_bank_account_repository)]
BankTransactionRepositoryDep = Annotated[
    BankTransactionRepository, Depends(get_bank_transaction_repository)
]
TreasuryServiceDep = Annotated[TreasuryService, Depends(get_treasury_service)]
AccountingRepositoryDep = Annotated[AccountingRepository, Depends(get_accounting_repository)]


def _account_read(
    account: BankAccount,
    summary: AccountBalanceSummary,
) -> BankAccountRead:
    """Combina la cuenta con sus saldos derivados."""
    return BankAccountRead(
        id=account.id,
        name=account.name,
        bank_name=account.bank_name,
        account_number=account.account_number,
        account_type=account.account_type,
        currency=account.currency,
        accounting_account_code=account.accounting_account_code,
        accounting_account_name=account.accounting_account_name,
        is_active=account.is_active,
        balance=summary.balance,
        reconciled_balance=summary.reconciled_balance,
        unreconciled_balance=summary.balance - summary.reconciled_balance,
        unreconciled_transactions=summary.unreconciled_count,
        version=account.version,
        created_at=account.created_at,
        updated_at=account.updated_at,
    )


@router.get("/puc-accounts", response_model=list[AccountingAccountRead])
def list_puc_accounts(
    repository: AccountingRepositoryDep,
) -> list[AccountingAccountRead]:
    """Lista el catálogo PUC disponible para configurar cuentas de tesorería."""
    accounts = repository.list_accounts(limit=100, offset=0)
    return [AccountingAccountRead.model_validate(account) for account in accounts]


@router.get("/accounts", response_model=list[BankAccountRead])
def list_bank_accounts(
    repository: BankAccountRepositoryDep,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[BankAccountRead]:
    """Lista cuentas bancarias con su saldo y estado de conciliación."""
    accounts = repository.list(limit=limit, offset=offset)
    balances = repository.get_balance_summaries()
    return [
        _account_read(
            account,
            balances.get(
                account.id,
                AccountBalanceSummary(
                    balance=Decimal("0.00"),
                    reconciled_balance=Decimal("0.00"),
                    unreconciled_count=0,
                ),
            ),
        )
        for account in accounts
    ]


@router.post(
    "/accounts",
    response_model=BankAccountRead,
    status_code=status.HTTP_201_CREATED,
)
def create_bank_account(
    payload: BankAccountCreate,
    db: DbSession,
    repository: BankAccountRepositoryDep,
    service: TreasuryServiceDep,
) -> BankAccountRead:
    """Registra una cuenta bancaria."""
    with operation_transaction(db):
        account = service.create_account(payload)
        summary = repository.get_balance_summary(account.id)
        result = _account_read(account, summary)
    return result


@router.get("/accounts/{account_id}", response_model=BankAccountRead)
def get_bank_account(
    account_id: UUID,
    repository: BankAccountRepositoryDep,
) -> BankAccountRead:
    """Obtiene una cuenta bancaria con sus saldos."""
    account = repository.get_by_id(account_id)
    if account is None:
        raise ResourceNotFoundError("Cuenta bancaria no encontrada")
    summary = repository.get_balance_summary(account_id)
    return _account_read(account, summary)


@router.patch("/accounts/{account_id}", response_model=BankAccountRead)
def update_bank_account(
    account_id: UUID,
    payload: BankAccountUpdate,
    db: DbSession,
    repository: BankAccountRepositoryDep,
    service: TreasuryServiceDep,
) -> BankAccountRead:
    """Actualiza el nombre o el estado de una cuenta bancaria."""
    with operation_transaction(db):
        account = service.update_account(account_id, payload)
        summary = repository.get_balance_summary(account.id)
        result = _account_read(account, summary)
    return result


@router.get(
    "/accounts/{account_id}/transactions",
    response_model=list[BankTransactionRead],
)
def list_bank_transactions(
    account_id: UUID,
    repository: BankAccountRepositoryDep,
    transactions: BankTransactionRepositoryDep,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[BankTransactionRead]:
    """Lista los movimientos propios y las transferencias recibidas."""
    if repository.get_by_id(account_id) is None:
        raise ResourceNotFoundError("Cuenta bancaria no encontrada")
    rows = transactions.list_by_account(account_id, limit=limit, offset=offset)
    return [BankTransactionRead.model_validate(row) for row in rows]


@router.post(
    "/accounts/{account_id}/transactions",
    response_model=BankTransactionRead,
    status_code=status.HTTP_201_CREATED,
)
def create_bank_transaction(
    account_id: UUID,
    payload: BankTransactionCreate,
    db: DbSession,
    service: TreasuryServiceDep,
) -> BankTransactionRead:
    """Registra un depósito, retiro o transferencia y su asiento contable."""
    with operation_transaction(db):
        transaction = service.create_transaction(account_id, payload)
        result = BankTransactionRead.model_validate(transaction)
    return result


@router.post(
    "/transactions/{transaction_id}/reconcile",
    response_model=BankTransactionRead,
)
def reconcile_bank_transaction(
    transaction_id: UUID,
    payload: ReconcileRequest,
    db: DbSession,
    service: TreasuryServiceDep,
) -> BankTransactionRead:
    """Marca un movimiento como conciliado con el extracto bancario."""
    with operation_transaction(db):
        transaction = service.set_reconciled(
            transaction_id,
            payload.version,
            reconciled=True,
        )
        result = BankTransactionRead.model_validate(transaction)
    return result


@router.post(
    "/transactions/{transaction_id}/unreconcile",
    response_model=BankTransactionRead,
)
def unreconcile_bank_transaction(
    transaction_id: UUID,
    payload: ReconcileRequest,
    db: DbSession,
    service: TreasuryServiceDep,
) -> BankTransactionRead:
    """Desmarca la conciliación de un movimiento."""
    with operation_transaction(db):
        transaction = service.set_reconciled(
            transaction_id,
            payload.version,
            reconciled=False,
        )
        result = BankTransactionRead.model_validate(transaction)
    return result


@router.get("/summary", response_model=TreasurySummary)
def get_treasury_summary(service: TreasuryServiceDep) -> TreasurySummary:
    """Devuelve los totales agregados de tesorería."""
    return service.summary()


__all__ = ["router"]
