"use client";

import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  ApiError,
  createBankTransaction,
  reconcileBankTransaction,
  unreconcileBankTransaction,
  updateBankAccount,
  type AccountingAccount,
  type BankAccount,
  type BankTransaction,
  type BankTransactionCreateInput,
  type BankTransactionType,
} from "@/lib/api";
import { formatCurrency } from "@/lib/format";

const inputClassName =
  "mt-1 block w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-950 shadow-sm outline-none transition focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20 disabled:cursor-not-allowed disabled:bg-slate-50 disabled:text-slate-500";

const numberFieldClassName = `${inputClassName} tabular-nums`;

const TRANSACTION_TYPES: { value: BankTransactionType; label: string }[] = [
  { value: "DEPOSIT", label: "Depósito" },
  { value: "WITHDRAWAL", label: "Retiro" },
  { value: "TRANSFER", label: "Transferencia" },
];

const transactionLabels: Record<BankTransactionType, string> = {
  DEPOSIT: "Depósito",
  WITHDRAWAL: "Retiro",
  TRANSFER: "Transferencia",
};

const accountTypeLabels: Record<string, string> = {
  CHECKING: "Cuenta corriente",
  SAVINGS: "Cuenta de ahorros",
};

interface TreasuryAccountDetailProps {
  account: BankAccount;
  accounts: BankAccount[];
  transactions: BankTransaction[];
  pucAccounts: AccountingAccount[];
  today: string;
}

function defaultCounterpartCode(
  type: BankTransactionType,
  pucAccounts: AccountingAccount[],
): string {
  const preferred = type === "WITHDRAWAL" ? "5199" : "413505";
  const match = pucAccounts.find((account) => account.code === preferred);
  if (match) {
    return match.code;
  }
  return pucAccounts[0]?.code ?? "";
}

export function TreasuryAccountDetail({
  account,
  accounts,
  transactions,
  pucAccounts,
  today,
}: TreasuryAccountDetailProps) {
  const router = useRouter();
  const otherAccounts = accounts.filter(
    (candidate) => candidate.id !== account.id && candidate.is_active,
  );
  const counterpartPucAccounts = pucAccounts.filter(
    (candidate) => candidate.code !== account.accounting_account_code,
  );

  const [transactionType, setTransactionType] =
    useState<BankTransactionType>("DEPOSIT");
  const [date, setDate] = useState(today);
  const [amount, setAmount] = useState("");
  const [description, setDescription] = useState("");
  const [reference, setReference] = useState("");
  const [counterpartAccountId, setCounterpartAccountId] = useState(
    otherAccounts[0]?.id ?? "",
  );
  const [counterpartCode, setCounterpartCode] = useState(
    defaultCounterpartCode("DEPOSIT", counterpartPucAccounts),
  );
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [busyTransactionId, setBusyTransactionId] = useState<string | null>(
    null,
  );
  const [isToggling, setIsToggling] = useState(false);

  function handleTypeChange(nextType: BankTransactionType): void {
    setTransactionType(nextType);
    setError(null);
    if (nextType !== "TRANSFER") {
      setCounterpartCode(defaultCounterpartCode(nextType, counterpartPucAccounts));
    }
  }

  async function handleSubmit(
    event: FormEvent<HTMLFormElement>,
  ): Promise<void> {
    event.preventDefault();

    const numericAmount = Number(amount);
    if (!Number.isFinite(numericAmount) || numericAmount <= 0) {
      setError("El monto debe ser un número mayor que cero.");
      return;
    }
    if (!description.trim()) {
      setError("La descripción es obligatoria.");
      return;
    }
    if (!date) {
      setError("La fecha es obligatoria.");
      return;
    }
    if (transactionType === "TRANSFER" && !counterpartAccountId) {
      setError("Selecciona la cuenta destino de la transferencia.");
      return;
    }
    if (transactionType !== "TRANSFER" && !counterpartCode) {
      setError("Selecciona la cuenta contable de contrapartida.");
      return;
    }

    setError(null);
    setIsSubmitting(true);

    try {
      const payload: BankTransactionCreateInput = {
        transaction_type: transactionType,
        date,
        amount,
        description: description.trim(),
        ...(reference.trim() ? { reference: reference.trim() } : {}),
        ...(transactionType === "TRANSFER"
          ? { counterpart_account_id: counterpartAccountId }
          : { counterpart_account_code: counterpartCode }),
      };
      await createBankTransaction(account.id, payload);
      setAmount("");
      setDescription("");
      setReference("");
      router.refresh();
    } catch (cause) {
      setError(
        cause instanceof ApiError
          ? `No se pudo registrar el movimiento: ${cause.message}`
          : "No se pudo registrar el movimiento. Revisa tu conexión e inténtalo de nuevo.",
      );
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handleToggleReconciliation(
    transaction: BankTransaction,
  ): Promise<void> {
    setError(null);
    setBusyTransactionId(transaction.id);
    try {
      if (transaction.is_reconciled) {
        await unreconcileBankTransaction(transaction.id, transaction.version);
      } else {
        await reconcileBankTransaction(transaction.id, transaction.version);
      }
      router.refresh();
    } catch (cause) {
      setError(
        cause instanceof ApiError
          ? `No se pudo actualizar la conciliación: ${cause.message}`
          : "No se pudo actualizar la conciliación. Inténtalo de nuevo.",
      );
    } finally {
      setBusyTransactionId(null);
    }
  }

  async function handleToggleActive(): Promise<void> {
    setError(null);
    setIsToggling(true);
    try {
      await updateBankAccount(account.id, {
        is_active: !account.is_active,
        version: account.version,
      });
      router.refresh();
    } catch (cause) {
      setError(
        cause instanceof ApiError
          ? `No se pudo actualizar la cuenta: ${cause.message}`
          : "No se pudo actualizar la cuenta. Inténtalo de nuevo.",
      );
    } finally {
      setIsToggling(false);
    }
  }

  return (
    <div className="space-y-6">
      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader>
            <CardDescription>Saldo en libros</CardDescription>
            <CardTitle className="text-2xl tabular-nums">
              {formatCurrency(account.balance, account.currency)}
            </CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader>
            <CardDescription>Conciliado</CardDescription>
            <CardTitle className="text-2xl tabular-nums text-emerald-700">
              {formatCurrency(account.reconciled_balance, account.currency)}
            </CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader>
            <CardDescription>Pendiente por conciliar</CardDescription>
            <CardTitle className="text-2xl tabular-nums text-amber-700">
              {formatCurrency(account.unreconciled_balance, account.currency)}
            </CardTitle>
            <p className="text-xs text-slate-500">
              {account.unreconciled_transactions} movimiento
              {account.unreconciled_transactions === 1 ? "" : "s"} sin conciliar
            </p>
          </CardHeader>
        </Card>
      </div>

      <Card>
        <CardHeader className="flex flex-row flex-wrap items-start justify-between gap-4">
          <div>
            <CardTitle>Datos de la cuenta</CardTitle>
            <CardDescription>
              {account.bank_name} · {account.account_number} ·{" "}
              {accountTypeLabels[account.account_type] ?? account.account_type}
            </CardDescription>
          </div>
          <button
            type="button"
            onClick={handleToggleActive}
            disabled={isToggling}
            className={`inline-flex items-center rounded-full px-3 py-1 text-xs font-semibold ring-1 ring-inset transition-colors disabled:opacity-50 ${
              account.is_active
                ? "bg-emerald-50 text-emerald-700 ring-emerald-200 hover:bg-emerald-100"
                : "bg-slate-100 text-slate-600 ring-slate-200 hover:bg-slate-200"
            }`}
          >
            {isToggling
              ? "Actualizando..."
              : account.is_active
                ? "Activa · desactivar"
                : "Inactiva · activar"}
          </button>
        </CardHeader>
        <CardContent>
          <dl className="grid gap-4 sm:grid-cols-3">
            <div>
              <dt className="text-xs font-semibold uppercase tracking-wider text-slate-500">
                Cuenta PUC
              </dt>
              <dd className="mt-1 text-sm text-slate-900">
                {account.accounting_account_code} ·{" "}
                {account.accounting_account_name}
              </dd>
            </div>
            <div>
              <dt className="text-xs font-semibold uppercase tracking-wider text-slate-500">
                Moneda
              </dt>
              <dd className="mt-1 text-sm text-slate-900">{account.currency}</dd>
            </div>
            <div>
              <dt className="text-xs font-semibold uppercase tracking-wider text-slate-500">
                Versión
              </dt>
              <dd className="mt-1 text-sm text-slate-900">{account.version}</dd>
            </div>
          </dl>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Registrar movimiento</CardTitle>
          <CardDescription>
            Cada movimiento genera su asiento contable automático. Los
            movimientos no se editan: para corregir, registra el movimiento
            inverso.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} noValidate className="space-y-4">
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              <div>
                <label
                  htmlFor="treasury-transaction-type"
                  className="block text-sm font-medium text-slate-700"
                >
                  Tipo{" "}
                  <span className="text-red-600" aria-hidden="true">
                    *
                  </span>
                </label>
                <select
                  id="treasury-transaction-type"
                  value={transactionType}
                  onChange={(event) =>
                    handleTypeChange(
                      event.target.value as BankTransactionType,
                    )
                  }
                  disabled={isSubmitting || !account.is_active}
                  className={inputClassName}
                >
                  {TRANSACTION_TYPES.map((type) => (
                    <option key={type.value} value={type.value}>
                      {type.label}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label
                  htmlFor="treasury-transaction-date"
                  className="block text-sm font-medium text-slate-700"
                >
                  Fecha{" "}
                  <span className="text-red-600" aria-hidden="true">
                    *
                  </span>
                </label>
                <input
                  id="treasury-transaction-date"
                  type="date"
                  required
                  value={date}
                  onChange={(event) => setDate(event.target.value)}
                  disabled={isSubmitting || !account.is_active}
                  className={inputClassName}
                />
              </div>

              <div>
                <label
                  htmlFor="treasury-transaction-amount"
                  className="block text-sm font-medium text-slate-700"
                >
                  Monto{" "}
                  <span className="text-red-600" aria-hidden="true">
                    *
                  </span>
                </label>
                <input
                  id="treasury-transaction-amount"
                  type="number"
                  min="0.01"
                  step="0.01"
                  inputMode="decimal"
                  required
                  value={amount}
                  onChange={(event) => setAmount(event.target.value)}
                  disabled={isSubmitting || !account.is_active}
                  className={numberFieldClassName}
                  placeholder="Ej. 1500000.00"
                />
              </div>

              <div>
                <label
                  htmlFor="treasury-transaction-reference"
                  className="block text-sm font-medium text-slate-700"
                >
                  Referencia{" "}
                  <span className="text-xs font-normal text-slate-400">
                    (opcional)
                  </span>
                </label>
                <input
                  id="treasury-transaction-reference"
                  type="text"
                  maxLength={100}
                  autoComplete="off"
                  value={reference}
                  onChange={(event) => setReference(event.target.value)}
                  disabled={isSubmitting || !account.is_active}
                  className={inputClassName}
                  placeholder="Ej. Extracto 1234"
                />
              </div>

              <div className="sm:col-span-2">
                <label
                  htmlFor="treasury-transaction-description"
                  className="block text-sm font-medium text-slate-700"
                >
                  Descripción{" "}
                  <span className="text-red-600" aria-hidden="true">
                    *
                  </span>
                </label>
                <input
                  id="treasury-transaction-description"
                  type="text"
                  required
                  maxLength={200}
                  autoComplete="off"
                  value={description}
                  onChange={(event) => setDescription(event.target.value)}
                  disabled={isSubmitting || !account.is_active}
                  className={inputClassName}
                  placeholder="Ej. Recaudo de factura 001"
                />
              </div>

              {transactionType === "TRANSFER" ? (
                <div className="sm:col-span-2">
                  <label
                    htmlFor="treasury-counterpart-account"
                    className="block text-sm font-medium text-slate-700"
                  >
                    Cuenta destino{" "}
                    <span className="text-red-600" aria-hidden="true">
                      *
                    </span>
                  </label>
                  <select
                    id="treasury-counterpart-account"
                    value={counterpartAccountId}
                    onChange={(event) =>
                      setCounterpartAccountId(event.target.value)
                    }
                    disabled={isSubmitting || !account.is_active}
                    className={inputClassName}
                  >
                    <option value="">Selecciona una cuenta</option>
                    {otherAccounts.map((candidate) => (
                      <option key={candidate.id} value={candidate.id}>
                        {candidate.name} · {candidate.bank_name} ·{" "}
                        {candidate.accounting_account_code}
                      </option>
                    ))}
                  </select>
                </div>
              ) : (
                <div className="sm:col-span-2">
                  <label
                    htmlFor="treasury-counterpart-code"
                    className="block text-sm font-medium text-slate-700"
                  >
                    Cuenta contable de contrapartida{" "}
                    <span className="text-red-600" aria-hidden="true">
                      *
                    </span>
                  </label>
                  <select
                    id="treasury-counterpart-code"
                    value={counterpartCode}
                    onChange={(event) => setCounterpartCode(event.target.value)}
                    disabled={isSubmitting || !account.is_active}
                    className={inputClassName}
                  >
                    {counterpartPucAccounts.map((candidate) => (
                      <option key={candidate.code} value={candidate.code}>
                        {candidate.code} · {candidate.name}
                      </option>
                    ))}
                  </select>
                  <p className="mt-1 text-xs text-slate-500">
                    Depósitos: crédito a la contrapartida. Retiros: débito a la
                    contrapartida.
                  </p>
                </div>
              )}
            </div>

            {error ? (
              <p
                role="alert"
                className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700"
              >
                {error}
              </p>
            ) : null}

            {!account.is_active ? (
              <p className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-700">
                La cuenta está inactiva. Actívala para registrar movimientos.
              </p>
            ) : null}

            <div className="flex justify-end">
              <Button
                type="submit"
                disabled={isSubmitting || !account.is_active}
                className="w-full sm:w-auto"
              >
                {isSubmitting ? "Registrando..." : "Registrar movimiento"}
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Movimientos</CardTitle>
          <CardDescription>
            {transactions.length} movimiento
            {transactions.length === 1 ? "" : "s"} registrado
            {transactions.length === 1 ? "" : "s"}.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {transactions.length === 0 ? (
            <div className="rounded-xl border border-dashed border-slate-300 bg-slate-50 px-6 py-10 text-center">
              <p className="font-medium text-slate-700">
                Todavía no hay movimientos
              </p>
              <p className="mt-1 text-sm text-slate-500">
                Registra el primer depósito, retiro o transferencia.
              </p>
            </div>
          ) : (
            <Table>
              <caption className="sr-only">
                Movimientos de la cuenta bancaria
              </caption>
              <TableHeader>
                <TableRow>
                  <TableHead>Fecha</TableHead>
                  <TableHead>Tipo</TableHead>
                  <TableHead>Descripción</TableHead>
                  <TableHead>Contrapartida</TableHead>
                  <TableHead className="text-right">Monto</TableHead>
                  <TableHead>Conciliación</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {transactions.map((transaction) => {
                  const isIncomingTransfer =
                    transaction.transaction_type === "TRANSFER" &&
                    transaction.counterpart_account_id === account.id;
                  const isIncoming =
                    transaction.transaction_type === "DEPOSIT" ||
                    isIncomingTransfer;
                  const label =
                    transaction.transaction_type === "TRANSFER"
                      ? isIncomingTransfer
                        ? "Transferencia recibida"
                        : "Transferencia enviada"
                      : transactionLabels[transaction.transaction_type];
                  const counterpart =
                    transaction.transaction_type === "TRANSFER"
                      ? transaction.counterpart_account_name ?? "—"
                      : transaction.counterpart_account_code ?? "—";

                  return (
                    <TableRow key={transaction.id}>
                      <TableCell className="text-slate-900">
                        {transaction.date}
                      </TableCell>
                      <TableCell className="text-slate-900">{label}</TableCell>
                      <TableCell className="text-slate-900">
                        {transaction.description}
                        {transaction.reference ? (
                          <span className="block text-xs text-slate-500">
                            Ref. {transaction.reference}
                          </span>
                        ) : null}
                      </TableCell>
                      <TableCell className="text-slate-600">
                        {counterpart}
                      </TableCell>
                      <TableCell
                        className={`text-right font-medium tabular-nums ${
                          isIncoming ? "text-emerald-700" : "text-rose-700"
                        }`}
                      >
                        {isIncoming ? "+" : "−"}
                        {formatCurrency(transaction.amount, account.currency)}
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center gap-2">
                          <span
                            className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-semibold ring-1 ring-inset ${
                              transaction.is_reconciled
                                ? "bg-emerald-50 text-emerald-700 ring-emerald-200"
                                : "bg-amber-50 text-amber-700 ring-amber-200"
                            }`}
                          >
                            {transaction.is_reconciled
                              ? "Conciliado"
                              : "Pendiente"}
                          </span>
                          <button
                            type="button"
                            onClick={() =>
                              handleToggleReconciliation(transaction)
                            }
                            disabled={busyTransactionId === transaction.id}
                            className="text-xs font-semibold text-indigo-600 transition-colors hover:text-indigo-800 disabled:opacity-50"
                          >
                            {busyTransactionId === transaction.id
                              ? "Guardando..."
                              : transaction.is_reconciled
                                ? "Desmarcar"
                                : "Conciliar"}
                          </button>
                        </div>
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
