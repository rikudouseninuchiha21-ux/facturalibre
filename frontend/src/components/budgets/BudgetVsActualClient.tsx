"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

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
import type { BudgetVsActualReport, CostCenter } from "@/lib/api";
import { formatCurrency } from "@/lib/format";

const inputClassName =
  "mt-1 block w-full rounded-lg border border-zinc-300 bg-white px-3 py-2 text-sm text-zinc-950 shadow-sm outline-none transition focus:border-violet-600 focus:ring-2 focus:ring-violet-500/10";

interface BudgetVsActualClientProps {
  report: BudgetVsActualReport | null;
  costCenters: CostCenter[];
  periodYear: number;
  periodMonth: number;
  costCenterId: string;
}

export function BudgetVsActualClient({
  report,
  costCenters,
  periodYear,
  periodMonth,
  costCenterId,
}: BudgetVsActualClientProps) {
  const router = useRouter();
  const [year, setYear] = useState(periodYear);
  const [month, setMonth] = useState(periodMonth);
  const [center, setCenter] = useState(costCenterId);
  const [levelFilter, setLevelFilter] = useState("");

  function handleFilter(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const params = new URLSearchParams({
      period_year: String(year),
      period_month: String(month),
    });
    if (center) params.set("cost_center_id", center);
    router.push(`/budget-vs-actual?${params.toString()}`);
  }

  const allBlocks = report?.blocks ?? [];
  const blocks = allBlocks
    .map((block) => ({
      ...block,
      lines:
        levelFilter === ""
          ? block.lines
          : block.lines.filter((line) => line.alert_level === levelFilter),
    }))
    .filter((block) => block.lines.length > 0);

  return (
    <>
      <Card>
        <CardHeader>
          <CardTitle>Filtros</CardTitle>
          <CardDescription>
            Elige el periodo y, opcionalmente, un centro de costo.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleFilter} className="space-y-4">
            <div className="grid gap-4 md:grid-cols-4">
              <div>
                <label
                  htmlFor="report-year"
                  className="text-xs font-medium text-slate-500"
                >
                  Año
                </label>
                <input
                  id="report-year"
                  type="number"
                  min={2000}
                  max={2100}
                  value={year}
                  onChange={(event) => setYear(Number(event.target.value))}
                  className={inputClassName}
                />
              </div>
              <div>
                <label
                  htmlFor="report-month"
                  className="text-xs font-medium text-slate-500"
                >
                  Mes
                </label>
                <select
                  id="report-month"
                  value={month}
                  onChange={(event) => setMonth(Number(event.target.value))}
                  className={inputClassName}
                >
                  {Array.from({ length: 12 }, (_, index) => index + 1).map(
                    (value) => (
                      <option key={value} value={value}>
                        {String(value).padStart(2, "0")}
                      </option>
                    ),
                  )}
                </select>
              </div>
              <div>
                <label
                  htmlFor="report-center"
                  className="text-xs font-medium text-slate-500"
                >
                  Centro de costo
                </label>
                <select
                  id="report-center"
                  value={center}
                  onChange={(event) => setCenter(event.target.value)}
                  className={inputClassName}
                >
                  <option value="">Todos</option>
                  {costCenters.map((costCenter) => (
                    <option key={costCenter.id} value={costCenter.id}>
                      {costCenter.code} — {costCenter.name}
                    </option>
                  ))}
                </select>
              </div>
              <div className="flex items-end">
                <button
                  type="submit"
                  className="inline-flex w-full items-center justify-center rounded-lg bg-gradient-to-br from-violet-600 to-violet-700 px-4 py-2 text-sm font-semibold text-white shadow-sm transition-colors hover:from-violet-700 hover:to-violet-800"
                >
                  Consultar
                </button>
              </div>
            </div>
          </form>

          <div className="flex items-center gap-3 border-t border-zinc-100 pt-4">
            <label
              htmlFor="report-level"
              className="text-xs font-medium text-slate-500"
            >
              Nivel de alerta
            </label>
            <select
              id="report-level"
              value={levelFilter}
              onChange={(event) => setLevelFilter(event.target.value)}
              className="rounded-lg border border-zinc-300 bg-white px-3 py-1.5 text-sm text-zinc-950 shadow-sm outline-none transition focus:border-violet-600 focus:ring-2 focus:ring-violet-500/10"
            >
              <option value="">Todos</option>
              <option value="WARNING">Atención (80–90%)</option>
              <option value="CRITICAL">Crítico (90–100%)</option>
              <option value="OVER">Sobregiro (≥100%)</option>
            </select>
          </div>
        </CardContent>
      </Card>

      {allBlocks.length === 0 ? (
        <Card>
          <CardContent>
            <div className="rounded-xl border border-dashed border-slate-300 bg-slate-50 px-6 py-10 text-center">
              <p className="font-medium text-slate-700">
                No hay presupuestos para este periodo
              </p>
              <p className="mt-1 text-sm text-slate-500">
                Crea presupuestos en la sección Presupuestos para compararlos
                contra el gasto real.
              </p>
            </div>
          </CardContent>
        </Card>
      ) : blocks.length === 0 ? (
        <Card>
          <CardContent>
            <div className="rounded-xl border border-dashed border-violet-200 bg-violet-50 px-6 py-10 text-center">
              <p className="font-medium text-violet-800">
                Ninguna cuenta tiene el nivel de alerta seleccionado
              </p>
              <p className="mt-1 text-sm text-violet-700">
                Cambia el filtro de nivel de alerta para ver más líneas.
              </p>
            </div>
          </CardContent>
        </Card>
      ) : (
        blocks.map((block) => {
          const chartData = block.lines.map((line) => ({
            label: line.account_code,
            Presupuestado: Number(line.budgeted),
            Real: Number(line.actual),
          }));
          return (
            <Card key={block.budget_id}>
              <CardHeader>
                <CardTitle>
                  {block.cost_center.code} — {block.cost_center.name}
                </CardTitle>
                <CardDescription>
                  {String(block.period_month).padStart(2, "0")}/
                  {block.period_year} · Estado {block.status} · Presupuestado{" "}
                  {formatCurrency(block.totals.budgeted, "COP")} · Real{" "}
                  {formatCurrency(block.totals.actual, "COP")} · Desviación{" "}
                  <span
                    className={
                      Number(block.totals.variance) > 0
                        ? "text-red-700"
                        : "text-emerald-700"
                    }
                  >
                    {formatCurrency(block.totals.variance, "COP")}
                  </span>
                  {block.totals.variance_pct !== null
                    ? ` (${block.totals.variance_pct}%)`
                    : ""}
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                <div
                  className="h-72 w-full"
                  role="img"
                  aria-label={`Presupuestado contra real por cuenta del centro ${block.cost_center.name}`}
                >
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart
                      data={chartData}
                      margin={{ top: 12, right: 8, left: 0, bottom: 0 }}
                    >
                      <CartesianGrid
                        vertical={false}
                        stroke="#e2e8f0"
                        strokeDasharray="4 4"
                      />
                      <XAxis
                        dataKey="label"
                        axisLine={false}
                        tickLine={false}
                        tick={{ fill: "#64748b", fontSize: 12 }}
                        dy={8}
                      />
                      <YAxis
                        axisLine={false}
                        tickLine={false}
                        tick={{ fill: "#64748b", fontSize: 12 }}
                        width={56}
                        tickFormatter={(value) =>
                          `${Math.round(Number(value) / 1_000_000)}M`
                        }
                      />
                      <Tooltip
                        cursor={{ fill: "rgba(148, 163, 184, 0.14)" }}
                        formatter={(value, name) => [
                          formatCurrency(String(value), "COP"),
                          String(name),
                        ]}
                        contentStyle={{
                          borderRadius: "0.75rem",
                          borderColor: "#e2e8f0",
                          boxShadow: "0 10px 30px rgba(15, 23, 42, 0.08)",
                          fontSize: "0.875rem",
                        }}
                      />
                      <Legend
                        wrapperStyle={{
                          fontSize: "0.875rem",
                          paddingTop: "0.5rem",
                        }}
                        iconType="circle"
                      />
                      <Bar
                        dataKey="Presupuestado"
                        fill="#d4d4d8"
                        radius={[6, 6, 0, 0]}
                        maxBarSize={40}
                      />
                      <Bar
                        dataKey="Real"
                        fill="url(#budgetActualAccentGradient)"
                        radius={[6, 6, 0, 0]}
                        maxBarSize={40}
                      />
                      <defs>
                        <linearGradient
                          id="budgetActualAccentGradient"
                          x1="0"
                          y1="0"
                          x2="0"
                          y2="1"
                        >
                          <stop offset="0%" stopColor="#8b5cf6" />
                          <stop offset="100%" stopColor="#7c3aed" />
                        </linearGradient>
                      </defs>
                    </BarChart>
                  </ResponsiveContainer>
                </div>

                <Table>
                  <caption className="sr-only">
                    Detalle presupuestado contra real por cuenta
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
                    {block.lines.map((line) => (
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
                          {line.variance_pct === null
                            ? "—"
                            : `${line.variance_pct}%`}
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
                </Table>
              </CardContent>
            </Card>
          );
        })
      )}
    </>
  );
}
