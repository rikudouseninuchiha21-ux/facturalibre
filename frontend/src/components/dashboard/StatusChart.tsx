"use client";

import {
  Cell,
  Legend,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
} from "recharts";

import type { InvoiceStatusSummary } from "@/lib/api";

interface StatusChartProps {
  data: InvoiceStatusSummary;
}

interface StatusDatum {
  name: string;
  value: number;
  color: string;
}

const STATUS_COLORS = {
  draft: "#a1a1aa",
  issued: "#10b981",
  void: "#f43f5e",
} as const;

function buildChartData(data: InvoiceStatusSummary): StatusDatum[] {
  return [
    { name: "Borradores", value: data.draft, color: STATUS_COLORS.draft },
    { name: "Emitidas", value: data.issued, color: STATUS_COLORS.issued },
    { name: "Anuladas", value: data.void, color: STATUS_COLORS.void },
  ];
}

function formatInvoiceCount(value: number): string {
  return `${value} ${value === 1 ? "factura" : "facturas"}`;
}

export function StatusChart({ data }: StatusChartProps) {
  const chartData = buildChartData(data);
  const total = chartData.reduce((sum, item) => sum + item.value, 0);

  if (total === 0) {
    return (
      <div className="flex h-72 items-center justify-center rounded-xl border border-dashed border-slate-300 bg-slate-50 px-6 text-center sm:h-80">
        <div>
          <p className="font-medium text-slate-700">Sin facturas registradas</p>
          <p className="mt-1 text-sm text-slate-500">
            El gráfico aparecerá cuando exista al menos una factura.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div
      className="h-72 w-full sm:h-80"
      role="img"
      aria-label={`Distribución de facturas por estado: ${chartData
        .map((item) => `${item.name}: ${item.value}`)
        .join(", ")}`}
    >
      <ResponsiveContainer width="100%" height="100%">
        <PieChart>
          <Pie
            data={chartData}
            dataKey="value"
            nameKey="name"
            cx="50%"
            cy="46%"
            innerRadius={58}
            outerRadius={96}
            paddingAngle={2}
            stroke="none"
          >
            {chartData.map((entry) => (
              <Cell key={entry.name} fill={entry.color} stroke="#fff" strokeWidth={2} />
            ))}
          </Pie>
          <Tooltip
            formatter={(value, name) => [
              formatInvoiceCount(Number(value)),
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
            verticalAlign="bottom"
            height={36}
            iconType="circle"
            formatter={(value) => (
              <span className="text-sm text-slate-600">{value}</span>
            )}
          />
        </PieChart>
      </ResponsiveContainer>
    </div>
  );
}
