"use client";

import {
  Bar,
  BarChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import type { MonthlySalesPoint } from "@/lib/api";
import { formatCurrency, formatMonth } from "@/lib/format";

interface SalesChartProps {
  data: MonthlySalesPoint[];
}

interface ChartDatum {
  month: string;
  label: string;
  total: number;
}

function buildChartData(data: MonthlySalesPoint[]): ChartDatum[] {
  return data.map((item) => {
    const [year, month] = item.month.split("-");
    const monthNumber = Number(month);
    const monthLabel = formatMonth(monthNumber);
    const shortMonth = monthLabel.slice(0, 3);

    return {
      month: item.month,
      label: `${shortMonth} ${year.slice(-2)}`,
      total: Number(item.total),
    };
  });
}

function formatTooltipLabel(label: string): string {
  const [year, month] = label.split("-");
  return `${formatMonth(Number(month))} ${year}`;
}

function formatCompactAmount(value: number): string {
  return new Intl.NumberFormat("es-CO", {
    notation: "compact",
    maximumFractionDigits: 1,
  }).format(value);
}

export function SalesChart({ data }: SalesChartProps) {
  const chartData = buildChartData(data);

  return (
    <div
      className="h-72 w-full sm:h-80"
      role="img"
      aria-label="Ventas facturadas en los últimos seis meses"
    >
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={chartData} margin={{ top: 12, right: 8, left: 0, bottom: 0 }}>
          <defs>
            <linearGradient id="barGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#818cf8" />
              <stop offset="100%" stopColor="#4f46e5" />
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
            formatter={(value) => [
              formatCurrency(String(value), "COP"),
              "Facturado",
            ]}
            labelFormatter={(label) => formatTooltipLabel(String(label))}
            contentStyle={{
              borderRadius: "0.75rem",
              borderColor: "#e2e8f0",
              boxShadow: "0 10px 30px rgba(15, 23, 42, 0.08)",
              fontSize: "0.875rem",
            }}
          />
          <Bar
            dataKey="total"
            name="Facturado"
            fill="url(#barGradient)"
            radius={[6, 6, 0, 0]}
            maxBarSize={56}
          />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
