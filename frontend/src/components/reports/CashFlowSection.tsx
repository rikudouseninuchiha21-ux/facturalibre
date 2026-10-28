"use client";

import {
  Bar,
  BarChart,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

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
import type {
  AgingBucketSummary,
  AgingReport,
  CashFlowMonth,
  CashFlowReport,
} from "@/lib/api";
import { formatCurrency, formatMonth } from "@/lib/format";

interface CashFlowSectionProps {
  aging: AgingReport;
  cashFlow: CashFlowReport;
}

interface CashFlowChartDatum {
  month: string;
  label: string;
  income: number;
  expenses: number;
}

function buildChartData(months: CashFlowMonth[]): CashFlowChartDatum[] {
  return months.map((item) => {
    const [year, month] = item.month.split("-");
    const monthLabel = formatMonth(Number(month));
    const shortMonth = monthLabel.slice(0, 3);

    return {
      month: item.month,
      label: `${shortMonth} ${year.slice(-2)}`,
      income: Number(item.income),
      expenses: Number(item.expenses),
    };
  });
}

function formatCompactAmount(value: number): string {
  return new Intl.NumberFormat("es-CO", {
    notation: "compact",
    maximumFractionDigits: 1,
  }).format(value);
}

function formatDate(value: string): string {
  const [year, month, day] = value.split("-").map(Number);
  return new Intl.DateTimeFormat("es-CO", {
    day: "2-digit",
    month: "long",
    year: "numeric",
  }).format(new Date(year, month - 1, day));
}

function daysOverdueClass(days: number): string {
  if (days > 90) {
    return "text-red-600";
  }
  if (days > 60) {
    return "text-amber-700";
  }
  if (days > 30) {
    return "text-amber-600";
  }
  return "text-emerald-600";
}

function MetricCard({
  label,
  value,
  description,
  tone,
}: {
  label: string;
  value: string;
  description: string;
  tone: "accent" | "danger" | "neutral";
}) {
  const toneStyles = {
    accent: "border-violet-200/80 bg-gradient-to-br from-violet-50 to-white",
    danger: "border-red-200/80 bg-gradient-to-br from-red-50 to-white",
    neutral: "border-zinc-200/80 bg-gradient-to-br from-zinc-50 to-white",
  } as const;
  const valueStyles = {
    accent: "text-violet-700",
    danger: "text-red-700",
    neutral: "text-zinc-950",
  } as const;

  return (
    <Card className={toneStyles[tone]}>
      <div className="p-5">
        <p className="text-xs font-semibold uppercase tracking-[0.16em] text-zinc-500">
          {label}
        </p>
        <p
          className={`mt-2 text-2xl font-bold tracking-tight tabular-nums ${valueStyles[tone]}`}
        >
          {value}
        </p>
        <p className="mt-1 text-xs leading-5 text-zinc-500">{description}</p>
      </div>
    </Card>
  );
}

function CashFlowChart({ months }: { months: CashFlowMonth[] }) {
  const chartData = buildChartData(months);

  return (
    <div
      className="h-72 w-full sm:h-80"
      role="img"
      aria-label="Ingresos y egresos de caja de los últimos seis meses"
    >
      <ResponsiveContainer width="100%" height="100%">
        <BarChart
          data={chartData}
          margin={{ top: 12, right: 8, left: 0, bottom: 0 }}
        >
          <defs>
            <linearGradient
              id="cashFlowIncomeGradient"
              x1="0"
              y1="0"
              x2="0"
              y2="1"
            >
              <stop offset="0%" stopColor="#8b5cf6" />
              <stop offset="100%" stopColor="#7c3aed" />
            </linearGradient>
          </defs>
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
            tickFormatter={(value) => formatCompactAmount(Number(value))}
            width={56}
          />
          <Tooltip
            cursor={{ fill: "rgba(148, 163, 184, 0.14)" }}
            formatter={(value, name) => [
              formatCurrency(String(value), "COP"),
              String(name),
            ]}
            labelFormatter={(label) => String(label)}
            contentStyle={{
              borderRadius: "0.75rem",
              borderColor: "#e2e8f0",
              boxShadow: "0 10px 30px rgba(15, 23, 42, 0.08)",
              fontSize: "0.875rem",
            }}
          />
          <Legend
            wrapperStyle={{ fontSize: "0.875rem", paddingTop: "0.5rem" }}
            iconType="circle"
          />
          <Bar
            dataKey="income"
            name="Ingresos"
            fill="url(#cashFlowIncomeGradient)"
            radius={[6, 6, 0, 0]}
            maxBarSize={30}
          />
          <Bar
            dataKey="expenses"
            name="Egresos"
            fill="#7c3aed"
            radius={[6, 6, 0, 0]}
            maxBarSize={30}
          />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

function AgingBucketList({ buckets }: { buckets: AgingBucketSummary[] }) {
  return (
    <div className="space-y-2">
      {buckets.map((bucket) => (
        <div
          key={bucket.key}
          className="flex items-center justify-between rounded-xl border border-violet-100 bg-violet-50/70 px-3 py-2"
        >
          <div>
            <p className="text-sm font-semibold text-violet-950">
              {bucket.label}
            </p>
            <p className="text-xs text-violet-700/80">
              {bucket.invoice_count} factura
              {bucket.invoice_count === 1 ? "" : "s"}
            </p>
          </div>
          <p className="text-sm font-semibold tabular-nums text-violet-950">
            {formatCurrency(bucket.total, "COP")}
          </p>
        </div>
      ))}
    </div>
  );
}

export function CashFlowSection({ aging, cashFlow }: CashFlowSectionProps) {
  return (
    <section className="space-y-4" aria-labelledby="cartera-liquidez-title">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-violet-600">
            Liquidez
          </p>
          <h2
            id="cartera-liquidez-title"
            className="mt-1 text-2xl font-bold tracking-tight text-zinc-950"
          >
            Cartera y Liquidez
          </h2>
          <p className="mt-1 max-w-2xl text-sm text-zinc-600">
            Flujo de caja real de los últimos seis meses y antigüedad de las
            cuentas por cobrar.
          </p>
        </div>
        <span className="rounded-full border border-violet-200 bg-violet-50 px-3 py-1 text-xs font-semibold text-violet-800">
          Corte: {formatDate(aging.as_of)}
        </span>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <MetricCard
          label="Cartera pendiente"
          value={formatCurrency(aging.total_receivable, "COP")}
          description={`${aging.clients.length} cliente${
            aging.clients.length === 1 ? "" : "s"
          } con saldo pendiente.`}
          tone="accent"
        />
        <MetricCard
          label="Proyección a 30 días"
          value={formatCurrency(
            cashFlow.projection.expected_collections,
            "COP",
          )}
          description={`${cashFlow.projection.invoice_count} factura${
            cashFlow.projection.invoice_count === 1 ? "" : "s"
          } por cobrar, incluido el saldo vencido.`}
          tone="neutral"
        />
        <MetricCard
          label="Saldo vencido"
          value={formatCurrency(cashFlow.projection.overdue_balance, "COP")}
          description="Cartera con fecha de vencimiento anterior al corte."
          tone="danger"
        />
      </div>

      <div className="grid gap-6 xl:grid-cols-5">
        <Card className="xl:col-span-3">
          <CardHeader>
            <CardTitle>Flujo de caja</CardTitle>
            <CardDescription>
              Ingresos vs. egresos reales por mes. Los egresos se muestran en
              morado oscuro y los ingresos en violeta.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <CashFlowChart months={cashFlow.months} />
          </CardContent>
        </Card>

        <Card className="xl:col-span-2">
          <CardHeader>
            <CardTitle>Rangos de cartera</CardTitle>
            <CardDescription>
              Distribución de las cuentas por cobrar según los días de mora.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <AgingBucketList buckets={aging.buckets} />
            <div className="flex items-center justify-between border-t border-zinc-200 pt-3">
              <span className="text-sm font-semibold text-zinc-700">
                Total cartera
              </span>
              <span className="text-base font-bold tabular-nums text-zinc-950">
                {formatCurrency(aging.total_receivable, "COP")}
              </span>
            </div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Aging de cartera</CardTitle>
          <CardDescription>
            Saldo pendiente por cliente y rango de vencimiento. La columna de
            mora muestra la factura más antigua del cliente.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Cliente</TableHead>
                <TableHead className="text-right">Total</TableHead>
                {aging.buckets.map((bucket) => (
                  <TableHead key={bucket.key} className="text-right">
                    {bucket.label}
                  </TableHead>
                ))}
                <TableHead className="text-right">Facturas</TableHead>
                <TableHead className="text-right">Días de mora</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {aging.clients.length === 0 ? (
                <TableRow>
                  <TableCell
                    colSpan={aging.buckets.length + 4}
                    className="py-8 text-center text-zinc-500"
                  >
                    No hay cuentas por cobrar pendientes.
                  </TableCell>
                </TableRow>
              ) : (
                aging.clients.map((client) => (
                  <TableRow key={client.contact_id}>
                    <TableCell className="font-medium text-zinc-950">
                      {client.contact_name}
                    </TableCell>
                    <TableCell className="text-right font-semibold tabular-nums text-zinc-950">
                      {formatCurrency(client.total_balance, "COP")}
                    </TableCell>
                    {aging.buckets.map((bucket) => (
                      <TableCell
                        key={`${client.contact_id}-${bucket.key}`}
                        className="text-right tabular-nums"
                      >
                        {formatCurrency(
                          client.buckets[bucket.key] ?? "0.00",
                          "COP",
                        )}
                      </TableCell>
                    ))}
                    <TableCell className="text-right tabular-nums">
                      {client.invoice_count}
                    </TableCell>
                    <TableCell
                      className={`text-right font-semibold tabular-nums ${daysOverdueClass(
                        client.max_days_overdue,
                      )}`}
                    >
                      {client.max_days_overdue} días
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </section>
  );
}
