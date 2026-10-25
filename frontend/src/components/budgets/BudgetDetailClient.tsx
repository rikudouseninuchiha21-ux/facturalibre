"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { AlertTriangle } from "lucide-react";

import { BudgetAlertBadge } from "@/components/budgets/BudgetAlertBadge";
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
  addBudgetLine,
  approveBudget,
  closeBudget,
  deleteBudget,
  deleteBudgetLine,
  getBudgetActuals,
  updateBudget,
  updateBudgetLine,
  type AccountingAccount,
  type Budget,
  type BudgetVsActualResponse,
} from "@/lib/api";
import { formatCurrency } from "@/lib/format";

const inputClassName =
  "mt-1 block w-full rounded-lg border border-zinc-300 bg-white px-3 py-2 text-sm text-zinc-950 shadow-sm outline-none transition focus:border-amber-600 focus:ring-2 focus:ring-amber-500/10 disabled:cursor-not-allowed disabled:bg-zinc-50 disabled:text-zinc-500";

interface BudgetDetailClientProps {
  initialBudget: Budget;
  accounts: AccountingAccount[];
}

export function BudgetDetailClient({
  initialBudget,
  accounts,
}: BudgetDetailClientProps) {
  const router = useRouter();
  const [budget, setBudget] = useState<Budget>(initialBudget);
  const [actuals, setActuals] = useState<BudgetVsActualResponse | null>(null);
  const [accountCode, setAccountCode] = useState(accounts[0]?.code ?? "");
  const [amount, setAmount] = useState("");
  const [lineNotes, setLineNotes] = useState("");
  const [name, setName] = useState(initialBudget.name ?? "");
  const [notes, setNotes] = useState(initialBudget.notes ?? "");
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const isDraft = budget.status === "DRAFT";

  useEffect(() => {
    let cancelled = false;
    getBudgetActuals(budget.id)
      .then((data) => {
        if (!cancelled) setActuals(data);
      })
      .catch(() => {
        if (!cancelled) setActuals(null);
      });
    return () => {
      cancelled = true;
    };
  }, [budget.id, budget.status, budget.lines.length]);

  async function run(action: () => Promise<void>, message: string) {
    setError(null);
    setSuccess(null);
    setBusy(true);
    try {
      await action();
      setSuccess(message);
      router.refresh();
    } catch (cause) {
      setError(
        cause instanceof ApiError
          ? cause.message
          : "No se pudo completar la operación.",
      );
    } finally {
      setBusy(false);
    }
  }

  async function reloadBudget() {
    const refreshed = await import("@/lib/api").then((mod) =>
      mod.getBudget(budget.id),
    );
    setBudget(refreshed);
  }

  const handleAddLine = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    return run(async () => {
      await addBudgetLine(budget.id, {
        account_code: accountCode,
        amount: amount.trim(),
        notes: lineNotes.trim() || undefined,
      });
      setAmount("");
      setLineNotes("");
      await reloadBudget();
    }, "Línea presupuestal agregada.");
  };

  const handleUpdateLine = (lineId: string, newAmount: string) =>
    run(async () => {
      await updateBudgetLine(budget.id, lineId, { amount: newAmount });
      await reloadBudget();
    }, "Monto actualizado.");

  const handleRemoveLine = (lineId: string) =>
    run(async () => {
      await deleteBudgetLine(budget.id, lineId);
      await reloadBudget();
    }, "Línea removida del presupuesto.");

  const handleSaveHeader = () =>
    run(async () => {
      await updateBudget(budget.id, {
        name: name.trim() || undefined,
        notes: notes.trim() || undefined,
      });
      await reloadBudget();
    }, "Cabecera actualizada.");

  const handleApprove = () =>
    run(async () => {
      await approveBudget(budget.id);
      await reloadBudget();
    }, "Presupuesto aprobado: queda inmutable.");

  const handleClose = () =>
    run(async () => {
      await closeBudget(budget.id);
      await reloadBudget();
    }, "Presupuesto cerrado.");

  const handleDelete = () =>
    run(async () => {
      await deleteBudget(budget.id);
      router.push("/budgets");
    }, "Presupuesto eliminado.");

  return (
    <div className="space-y-6">
      {actuals &&
      (actuals.totals.alert_level_total === "CRITICAL" ||
        actuals.totals.alert_level_total === "OVER") ? (
        <div
          role="alert"
          className="flex items-start gap-3 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700"
        >
          <AlertTriangle className="mt-0.5 size-5 shrink-0" aria-hidden="true" />
          <p>
            <span className="font-semibold">
              {actuals.totals.alert_level_total === "OVER"
                ? "Sobregiro presupuestal:"
                : "Presupuesto en nivel crítico:"}
            </span>{" "}
            la utilización va en {actuals.totals.utilization_pct_total}% (
            {formatCurrency(actuals.totals.actual, "COP")} de{" "}
            {formatCurrency(actuals.totals.budgeted, "COP")} presupuestados).
          </p>
        </div>
      ) : null}

      <Card>
        <CardHeader>
          <CardTitle>Cabecera</CardTitle>
          <CardDescription>
            {isDraft
              ? "Editable mientras esté en borrador."
              : "El presupuesto no está en borrador: la cabecera y las líneas son de solo lectura."}
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="grid gap-6 md:grid-cols-2">
            <div className="space-y-2">
              <label
                htmlFor="budget-detail-name"
                className="block text-sm font-medium text-zinc-700"
              >
                Nombre
              </label>
              <input
                id="budget-detail-name"
                type="text"
                maxLength={150}
                value={name}
                onChange={(event) => setName(event.target.value)}
                disabled={!isDraft || busy}
                className={inputClassName}
              />
            </div>
            <div className="space-y-2">
              <label
                htmlFor="budget-detail-notes"
                className="block text-sm font-medium text-zinc-700"
              >
                Notas
              </label>
              <input
                id="budget-detail-notes"
                type="text"
                maxLength={2000}
                value={notes}
                onChange={(event) => setNotes(event.target.value)}
                disabled={!isDraft || busy}
                className={inputClassName}
              />
            </div>
          </div>
          <div className="flex flex-wrap items-center justify-between gap-3 border-t border-zinc-200 pt-4">
            <p className="text-sm text-zinc-600">
              Total presupuestado:{" "}
              <span className="text-lg font-bold tabular-nums text-zinc-950">
                {formatCurrency(budget.total, "COP")}
              </span>
            </p>
            <div className="flex flex-wrap gap-3">
              {isDraft ? (
                <button
                  type="button"
                  onClick={() => void handleSaveHeader()}
                  disabled={busy}
                  className="rounded-lg border border-zinc-300 bg-white px-4 py-2 text-sm font-semibold text-zinc-700 shadow-sm transition-colors hover:border-zinc-400 hover:bg-zinc-50 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  Guardar cabecera
                </button>
              ) : null}
              {isDraft ? (
                <button
                  type="button"
                  onClick={() => void handleApprove()}
                  disabled={busy}
                  className="inline-flex items-center justify-center rounded-lg bg-gradient-to-br from-amber-400 to-amber-600 px-4 py-2 text-sm font-semibold text-zinc-950 shadow-sm transition-colors hover:from-amber-300 hover:to-amber-500 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  Aprobar
                </button>
              ) : null}
              {budget.status === "APPROVED" ? (
                <button
                  type="button"
                  onClick={() => void handleClose()}
                  disabled={busy}
                  className="rounded-lg bg-zinc-950 px-4 py-2 text-sm font-semibold text-white shadow-sm transition-colors hover:bg-zinc-800 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  Cerrar
                </button>
              ) : null}
              {isDraft ? (
                <button
                  type="button"
                  onClick={() => void handleDelete()}
                  disabled={busy}
                  className="rounded-lg border border-red-200 bg-white px-4 py-2 text-sm font-semibold text-red-700 shadow-sm transition-colors hover:bg-red-50 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  Eliminar
                </button>
              ) : null}
            </div>
          </div>

          {error ? (
            <div
              role="alert"
              className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700"
            >
              {error}
            </div>
          ) : null}
          {success ? (
            <div
              role="status"
              className="rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-700"
            >
              {success}
            </div>
          ) : null}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Líneas por cuenta PUC</CardTitle>
          <CardDescription>
            {isDraft
              ? "Cada línea presupuesta el gasto de una cuenta para el centro de costo en el mes."
              : "Solo lectura: el presupuesto ya no está en borrador."}
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {isDraft ? (
            <form onSubmit={handleAddLine} className="space-y-4">
              <div className="grid gap-4 md:grid-cols-3">
                <div>
                  <label
                    htmlFor="line-account"
                    className="text-xs font-medium text-slate-500"
                  >
                    Cuenta PUC
                  </label>
                  <select
                    id="line-account"
                    required
                    value={accountCode}
                    onChange={(event) => setAccountCode(event.target.value)}
                    disabled={busy}
                    className={inputClassName}
                  >
                    {accounts.map((account) => (
                      <option key={account.code} value={account.code}>
                        {account.code} — {account.name}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label
                    htmlFor="line-amount"
                    className="text-xs font-medium text-slate-500"
                  >
                    Monto presupuestado
                  </label>
                  <input
                    id="line-amount"
                    type="number"
                    step="0.01"
                    min="0"
                    required
                    value={amount}
                    onChange={(event) => setAmount(event.target.value)}
                    disabled={busy}
                    className={inputClassName}
                    placeholder="1000000.00"
                  />
                </div>
                <div>
                  <label
                    htmlFor="line-notes"
                    className="text-xs font-medium text-slate-500"
                  >
                    Notas
                  </label>
                  <input
                    id="line-notes"
                    type="text"
                    maxLength={2000}
                    value={lineNotes}
                    onChange={(event) => setLineNotes(event.target.value)}
                    disabled={busy}
                    className={inputClassName}
                  />
                </div>
              </div>
              <div className="flex justify-end">
                <button
                  type="submit"
                  disabled={busy || accounts.length === 0}
                  className="rounded-lg border border-zinc-300 bg-white px-4 py-2 text-sm font-semibold text-zinc-700 shadow-sm transition-colors hover:border-amber-500 hover:text-amber-700 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  Agregar línea
                </button>
              </div>
            </form>
          ) : null}

          {budget.lines.length === 0 ? (
            <div className="rounded-xl border border-dashed border-slate-300 bg-slate-50 px-6 py-10 text-center">
              <p className="font-medium text-slate-700">
                El presupuesto no tiene líneas
              </p>
              {isDraft ? (
                <p className="mt-1 text-sm text-slate-500">
                  Agrega al menos una cuenta PUC para poder aprobarlo.
                </p>
              ) : null}
            </div>
          ) : (
            <Table>
              <caption className="sr-only">Líneas del presupuesto</caption>
              <TableHeader>
                <TableRow>
                  <TableHead>Cuenta</TableHead>
                  <TableHead>Nombre</TableHead>
                  <TableHead>Notas</TableHead>
                  <TableHead className="text-right">Monto</TableHead>
                  {isDraft ? <TableHead className="text-right">Acciones</TableHead> : null}
                </TableRow>
              </TableHeader>
              <TableBody>
                {budget.lines.map((line) => (
                  <TableRow key={line.id}>
                    <TableCell className="font-mono text-xs font-semibold text-slate-950">
                      {line.account_code}
                    </TableCell>
                    <TableCell className="text-slate-900">
                      {line.account_name}
                    </TableCell>
                    <TableCell className="max-w-xs truncate text-slate-600">
                      {line.notes ?? "—"}
                    </TableCell>
                    <TableCell className="text-right">
                      {isDraft ? (
                        <input
                          type="number"
                          step="0.01"
                          min="0"
                          defaultValue={line.amount}
                          onBlur={(event) => {
                            const value = event.target.value.trim();
                            if (value && value !== line.amount) {
                              void handleUpdateLine(line.id, value);
                            }
                          }}
                          disabled={busy}
                          className="w-36 rounded-lg border border-zinc-300 bg-white px-2 py-1 text-right text-sm tabular-nums text-zinc-950 shadow-sm outline-none transition focus:border-amber-600 focus:ring-2 focus:ring-amber-500/10"
                          aria-label={`Monto de la cuenta ${line.account_code}`}
                        />
                      ) : (
                        <span className="font-semibold tabular-nums text-slate-950">
                          {formatCurrency(line.amount, "COP")}
                        </span>
                      )}
                    </TableCell>
                    {isDraft ? (
                      <TableCell className="text-right">
                        <button
                          type="button"
                          onClick={() => void handleRemoveLine(line.id)}
                          disabled={busy}
                          className="rounded-lg border border-red-200 bg-white px-3 py-1.5 text-xs font-semibold text-red-700 shadow-sm transition-colors hover:bg-red-50 disabled:cursor-not-allowed disabled:opacity-50"
                        >
                          Quitar
                        </button>
                      </TableCell>
                    ) : null}
                  </TableRow>
                ))}
              </TableBody>
              <tfoot className="bg-slate-50 font-semibold text-slate-950">
                <tr>
                  <td className="px-4 py-3" colSpan={isDraft ? 4 : 3}>
                    Total
                  </td>
                  <td className="px-4 py-3 text-right tabular-nums">
                    {formatCurrency(budget.total, "COP")}
                  </td>
                  {isDraft ? <td /> : null}
                </tr>
              </tfoot>
            </Table>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Presupuesto vs Real</CardTitle>
          <CardDescription>
            El gasto real se deriva de los asientos contables del mes
            etiquetados con este centro de costo (compras, gastos y nómina).
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {!actuals ? (
            <p className="text-sm text-slate-500">
              No se pudo calcular la comparación contra el gasto real.
            </p>
          ) : actuals.lines.length === 0 ? (
            <p className="text-sm text-slate-500">
              Agrega líneas al presupuesto para compararlas contra el gasto
              real.
            </p>
          ) : (
            <>
              <div className="rounded-xl border border-zinc-200 bg-gradient-to-br from-amber-50 to-white p-4">
                <p className="text-sm text-zinc-600">
                  Presupuesto{" "}
                  <span className="font-semibold text-zinc-950">
                    {formatCurrency(actuals.totals.budgeted, "COP")}
                  </span>{" "}
                  · Ejecutado{" "}
                  <span className="font-semibold text-zinc-950">
                    {formatCurrency(actuals.totals.actual, "COP")}
                  </span>{" "}
                  · Utilización{" "}
                  <span
                    className={`font-bold ${
                      actuals.totals.alert_level_total === "OVER"
                        ? "text-red-700"
                        : actuals.totals.alert_level_total === "CRITICAL"
                          ? "text-orange-700"
                          : "text-amber-700"
                    }`}
                  >
                    {actuals.totals.utilization_pct_total === null
                      ? "N/A"
                      : `${actuals.totals.utilization_pct_total}%`}
                  </span>
                </p>
                <div
                  className="mt-3 h-3 w-full overflow-hidden rounded-full bg-zinc-200"
                  role="progressbar"
                  aria-valuenow={
                    actuals.totals.utilization_pct_total
                      ? Number(actuals.totals.utilization_pct_total)
                      : undefined
                  }
                  aria-valuemin={0}
                  aria-valuemax={100}
                  aria-label="Utilización del presupuesto"
                >
                  <div
                    className={`h-full rounded-full ${
                      actuals.totals.alert_level_total === "OVER"
                        ? "bg-red-500"
                        : actuals.totals.alert_level_total === "CRITICAL"
                          ? "bg-orange-500"
                          : "bg-gradient-to-r from-amber-300 to-amber-600"
                    }`}
                    style={{
                      width: `${Math.min(
                        Number(actuals.totals.utilization_pct_total ?? 0),
                        100,
                      )}%`,
                    }}
                  />
                </div>
                <div className="mt-2 flex items-center justify-between">
                  <span className="text-xs text-zinc-500">
                    Desviación:{" "}
                    {formatCurrency(actuals.totals.variance, "COP")}
                    {actuals.totals.variance_pct !== null
                      ? ` (${actuals.totals.variance_pct}%)`
                      : ""}
                  </span>
                  <BudgetAlertBadge
                    level={actuals.totals.alert_level_total}
                    utilizationPct={actuals.totals.utilization_pct_total}
                  />
                </div>
              </div>

              <Table>
                <caption className="sr-only">
                  Comparación presupuestado contra real por cuenta
                </caption>
                <TableHeader>
                  <TableRow>
                    <TableHead>Cuenta</TableHead>
                    <TableHead className="text-right">Presupuestado</TableHead>
                    <TableHead className="text-right">Real</TableHead>
                    <TableHead className="text-right">Desviación</TableHead>
                    <TableHead className="text-right">%</TableHead>
                    <TableHead>Alerta</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {actuals.lines.map((line) => (
                    <TableRow key={line.account_code}>
                      <TableCell className="text-slate-900">
                        <span className="font-mono text-xs font-semibold">
                          {line.account_code}
                        </span>{" "}
                        {line.account_name}
                      </TableCell>
                      <TableCell className="text-right tabular-nums text-slate-900">
                        {formatCurrency(line.budgeted, "COP")}
                      </TableCell>
                      <TableCell className="text-right tabular-nums text-slate-900">
                        {formatCurrency(line.actual, "COP")}
                      </TableCell>
                      <TableCell
                        className={`text-right font-semibold tabular-nums ${
                          Number(line.variance) > 0
                            ? "text-red-700"
                            : "text-emerald-700"
                        }`}
                      >
                        {formatCurrency(line.variance, "COP")}
                      </TableCell>
                      <TableCell className="text-right tabular-nums text-slate-600">
                        {line.variance_pct === null ? "—" : `${line.variance_pct}%`}
                      </TableCell>
                      <TableCell>
                        <BudgetAlertBadge
                          level={line.alert_level}
                          utilizationPct={line.utilization_pct}
                        />
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
                <tfoot className="bg-slate-50 font-semibold text-slate-950">
                  <tr>
                    <td className="px-4 py-3">Totales</td>
                    <td className="px-4 py-3 text-right tabular-nums">
                      {formatCurrency(actuals.totals.budgeted, "COP")}
                    </td>
                    <td className="px-4 py-3 text-right tabular-nums">
                      {formatCurrency(actuals.totals.actual, "COP")}
                    </td>
                    <td className="px-4 py-3 text-right tabular-nums">
                      {formatCurrency(actuals.totals.variance, "COP")}
                    </td>
                    <td className="px-4 py-3 text-right tabular-nums">
                      {actuals.totals.variance_pct === null
                        ? "—"
                        : `${actuals.totals.variance_pct}%`}
                    </td>
                    <td className="px-4 py-3">
                      <BudgetAlertBadge
                        level={actuals.totals.alert_level_total}
                        utilizationPct={actuals.totals.utilization_pct_total}
                      />
                    </td>
                  </tr>
                </tfoot>
              </Table>
            </>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
