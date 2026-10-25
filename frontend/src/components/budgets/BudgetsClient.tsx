"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

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
  createBudget,
  getBudgetAlerts,
  type Budget,
  type BudgetAlertItem,
  type BudgetStatus,
  type CostCenter,
} from "@/lib/api";
import { formatCurrency } from "@/lib/format";

const inputClassName =
  "mt-1 block w-full rounded-lg border border-zinc-300 bg-white px-3 py-2 text-sm text-zinc-950 shadow-sm outline-none transition focus:border-amber-600 focus:ring-2 focus:ring-amber-500/10 disabled:cursor-not-allowed disabled:bg-zinc-50 disabled:text-zinc-500";

const STATUS_LABELS: Record<BudgetStatus, string> = {
  DRAFT: "Borrador",
  APPROVED: "Aprobado",
  CLOSED: "Cerrado",
};

const STATUS_STYLES: Record<BudgetStatus, string> = {
  DRAFT: "bg-sky-50 text-sky-700 ring-sky-200",
  APPROVED: "bg-emerald-50 text-emerald-700 ring-emerald-200",
  CLOSED: "bg-zinc-100 text-zinc-600 ring-zinc-200",
};

interface BudgetsClientProps {
  initialBudgets: Budget[];
  costCenters: CostCenter[];
}

export function BudgetsClient({ initialBudgets, costCenters }: BudgetsClientProps) {
  const router = useRouter();
  const today = new Date();
  const [budgets, setBudgets] = useState<Budget[]>(initialBudgets);
  const [filterYear, setFilterYear] = useState(today.getFullYear());
  const [filterMonth, setFilterMonth] = useState(today.getMonth() + 1);
  const [filterCenter, setFilterCenter] = useState("");
  const [filterStatus, setFilterStatus] = useState("");
  const [newCenter, setNewCenter] = useState(costCenters[0]?.id ?? "");
  const [newYear, setNewYear] = useState(today.getFullYear());
  const [newMonth, setNewMonth] = useState(today.getMonth() + 1);
  const [newName, setNewName] = useState("");
  const [alerts, setAlerts] = useState<BudgetAlertItem[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Nivel de alerta por presupuesto del periodo filtrado (calculado por el
  // backend; el frontend nunca recalcula umbrales).
  useEffect(() => {
    let cancelled = false;
    getBudgetAlerts(filterYear, filterMonth)
      .then((data) => {
        if (!cancelled) setAlerts(data);
      })
      .catch(() => {
        if (!cancelled) setAlerts([]);
      });
    return () => {
      cancelled = true;
    };
  }, [filterYear, filterMonth, initialBudgets]);

  const alertByBudget = useMemo(
    () =>
      new Map(
        alerts.map((item) => [item.budget_id, item] as const),
      ),
    [alerts],
  );

  const filtered = useMemo(
    () =>
      budgets.filter((budget) => {
        if (budget.period_year !== filterYear) return false;
        if (budget.period_month !== filterMonth) return false;
        if (filterCenter && budget.cost_center.id !== filterCenter) return false;
        if (filterStatus && budget.status !== filterStatus) return false;
        return true;
      }),
    [budgets, filterYear, filterMonth, filterCenter, filterStatus],
  );

  async function handleCreate(
    event: React.FormEvent<HTMLFormElement>,
  ): Promise<void> {
    event.preventDefault();
    setError(null);
    setSuccess(null);
    setIsSubmitting(true);
    try {
      const created = await createBudget({
        cost_center_id: newCenter,
        period_year: newYear,
        period_month: newMonth,
        name: newName.trim() || undefined,
      });
      setBudgets((current) => [created, ...current]);
      setNewName("");
      setSuccess(
        `Presupuesto de ${created.cost_center.name} para ${String(newMonth).padStart(2, "0")}/${newYear} creado en borrador.`,
      );
      router.refresh();
    } catch (cause) {
      setError(
        cause instanceof ApiError
          ? cause.message
          : "No se pudo crear el presupuesto.",
      );
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <>
      <Card>
        <CardHeader>
          <CardTitle>Nuevo Presupuesto</CardTitle>
          <CardDescription>
            Un centro de costo solo puede tener un presupuesto por mes. El
            presupuesto nace en borrador y se aprueba desde su detalle.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleCreate} className="space-y-6">
            <div className="grid gap-6 md:grid-cols-4">
              <div className="space-y-2">
                <label
                  htmlFor="budget-center"
                  className="block text-sm font-medium text-zinc-700"
                >
                  Centro de costo{" "}
                  <span className="text-red-600" aria-hidden="true">
                    *
                  </span>
                </label>
                <select
                  id="budget-center"
                  required
                  value={newCenter}
                  onChange={(event) => setNewCenter(event.target.value)}
                  disabled={isSubmitting || costCenters.length === 0}
                  className={inputClassName}
                >
                  {costCenters.length === 0 ? (
                    <option value="">Sin centros activos</option>
                  ) : null}
                  {costCenters.map((center) => (
                    <option key={center.id} value={center.id}>
                      {center.code} — {center.name}
                    </option>
                  ))}
                </select>
              </div>
              <div className="space-y-2">
                <label
                  htmlFor="budget-year"
                  className="block text-sm font-medium text-zinc-700"
                >
                  Año{" "}
                  <span className="text-red-600" aria-hidden="true">
                    *
                  </span>
                </label>
                <input
                  id="budget-year"
                  type="number"
                  required
                  min={2000}
                  max={2100}
                  value={newYear}
                  onChange={(event) => setNewYear(Number(event.target.value))}
                  disabled={isSubmitting}
                  className={inputClassName}
                />
              </div>
              <div className="space-y-2">
                <label
                  htmlFor="budget-month"
                  className="block text-sm font-medium text-zinc-700"
                >
                  Mes{" "}
                  <span className="text-red-600" aria-hidden="true">
                    *
                  </span>
                </label>
                <select
                  id="budget-month"
                  required
                  value={newMonth}
                  onChange={(event) => setNewMonth(Number(event.target.value))}
                  disabled={isSubmitting}
                  className={inputClassName}
                >
                  {Array.from({ length: 12 }, (_, index) => index + 1).map(
                    (month) => (
                      <option key={month} value={month}>
                        {String(month).padStart(2, "0")}
                      </option>
                    ),
                  )}
                </select>
              </div>
              <div className="space-y-2">
                <label
                  htmlFor="budget-name"
                  className="block text-sm font-medium text-zinc-700"
                >
                  Nombre
                </label>
                <input
                  id="budget-name"
                  type="text"
                  maxLength={150}
                  value={newName}
                  onChange={(event) => setNewName(event.target.value)}
                  disabled={isSubmitting}
                  className={inputClassName}
                  placeholder="Gastos administrativos"
                />
              </div>
            </div>
            <div className="flex justify-end">
              <button
                type="submit"
                disabled={isSubmitting || costCenters.length === 0}
                className="inline-flex items-center justify-center rounded-lg bg-gradient-to-br from-amber-400 to-amber-600 px-4 py-2 text-sm font-semibold text-zinc-950 shadow-sm transition-colors hover:from-amber-300 hover:to-amber-500 disabled:cursor-not-allowed disabled:opacity-50"
              >
                {isSubmitting ? "Creando..." : "Nuevo Presupuesto"}
              </button>
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
          </form>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Listado</CardTitle>
          <CardDescription>
            {filtered.length} presupuesto{filtered.length === 1 ? "" : "s"} para
            el periodo seleccionado.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-4 md:grid-cols-4">
            <div>
              <label
                htmlFor="filter-year"
                className="text-xs font-medium text-slate-500"
              >
                Año
              </label>
              <input
                id="filter-year"
                type="number"
                min={2000}
                max={2100}
                value={filterYear}
                onChange={(event) => setFilterYear(Number(event.target.value))}
                className={inputClassName}
              />
            </div>
            <div>
              <label
                htmlFor="filter-month"
                className="text-xs font-medium text-slate-500"
              >
                Mes
              </label>
              <select
                id="filter-month"
                value={filterMonth}
                onChange={(event) => setFilterMonth(Number(event.target.value))}
                className={inputClassName}
              >
                {Array.from({ length: 12 }, (_, index) => index + 1).map(
                  (month) => (
                    <option key={month} value={month}>
                      {String(month).padStart(2, "0")}
                    </option>
                  ),
                )}
              </select>
            </div>
            <div>
              <label
                htmlFor="filter-center"
                className="text-xs font-medium text-slate-500"
              >
                Centro de costo
              </label>
              <select
                id="filter-center"
                value={filterCenter}
                onChange={(event) => setFilterCenter(event.target.value)}
                className={inputClassName}
              >
                <option value="">Todos</option>
                {costCenters.map((center) => (
                  <option key={center.id} value={center.id}>
                    {center.name}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label
                htmlFor="filter-status"
                className="text-xs font-medium text-slate-500"
              >
                Estado
              </label>
              <select
                id="filter-status"
                value={filterStatus}
                onChange={(event) => setFilterStatus(event.target.value)}
                className={inputClassName}
              >
                <option value="">Todos</option>
                {Object.entries(STATUS_LABELS).map(([value, label]) => (
                  <option key={value} value={value}>
                    {label}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {filtered.length === 0 ? (
            <div className="rounded-xl border border-dashed border-slate-300 bg-slate-50 px-6 py-10 text-center">
              <p className="font-medium text-slate-700">
                No hay presupuestos para este filtro
              </p>
              <p className="mt-1 text-sm text-slate-500">
                Crea uno con el formulario de arriba o cambia el periodo.
              </p>
            </div>
          ) : (
            <Table>
              <caption className="sr-only">Listado de presupuestos</caption>
              <TableHeader>
                <TableRow>
                  <TableHead>Periodo</TableHead>
                  <TableHead>Centro de costo</TableHead>
                  <TableHead>Nombre</TableHead>
                  <TableHead>Estado</TableHead>
                  <TableHead>Alerta</TableHead>
                  <TableHead className="text-right">Líneas</TableHead>
                  <TableHead className="text-right">Total</TableHead>
                  <TableHead className="text-right">Acción</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filtered.map((budget) => {
                  const alert = alertByBudget.get(budget.id);
                  return (
                    <TableRow key={budget.id}>
                      <TableCell className="font-medium tabular-nums text-slate-950">
                        {String(budget.period_month).padStart(2, "0")}/
                        {budget.period_year}
                      </TableCell>
                      <TableCell className="text-slate-900">
                        {budget.cost_center.name}
                      </TableCell>
                      <TableCell className="max-w-xs truncate text-slate-600">
                        {budget.name ?? "—"}
                      </TableCell>
                      <TableCell>
                        <span
                          className={`inline-flex items-center rounded-full px-2.5 py-1 text-xs font-semibold ring-1 ring-inset ${STATUS_STYLES[budget.status]}`}
                        >
                          {STATUS_LABELS[budget.status]}
                        </span>
                      </TableCell>
                      <TableCell>
                        {alert ? (
                          <BudgetAlertBadge
                            level={alert.alert_level}
                            utilizationPct={alert.utilization_pct}
                          />
                        ) : (
                          <span className="text-xs text-slate-400">—</span>
                        )}
                      </TableCell>
                      <TableCell className="text-right tabular-nums text-slate-900">
                        {budget.lines.length}
                      </TableCell>
                      <TableCell className="text-right font-semibold tabular-nums text-slate-950">
                        {formatCurrency(budget.total, "COP")}
                      </TableCell>
                      <TableCell className="text-right">
                        <Link
                          href={`/budgets/${budget.id}`}
                          className="inline-flex items-center rounded-lg border border-zinc-300 bg-white px-3 py-1.5 text-xs font-semibold text-zinc-700 shadow-sm transition-colors hover:border-amber-500 hover:text-amber-700"
                        >
                          Ver detalle
                        </Link>
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </>
  );
}
