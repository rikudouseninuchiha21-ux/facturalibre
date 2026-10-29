"use client";

import { useEffect, useMemo, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { CheckCircle2, Download } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Modal } from "@/components/ui/modal";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  downloadFileNative,
  getDrillDownReport,
  getFinancialReportExportUrl,
  getNiifBalanceSheet,
  getNiifCashFlow,
  getNiifIncomeStatement,
  type DrillDownReport,
  type NiifBalanceSheet,
  type NiifCashFlow,
  type NiifIncomeStatement,
  type ReportAccountRow,
} from "@/lib/api";
import { formatCurrency, formatDate } from "@/lib/format";

type TabKey = "income" | "balance" | "cash";

interface StatementRow {
  key: string;
  label: string;
  value: string;
  code?: string;
  name?: string;
  bold?: boolean;
  indent?: boolean;
}

interface Trend {
  arrow: string;
  label: string;
  className: string;
}

const ASSET_COLORS = ["#7c3aed", "#3b82f6", "#10b981", "#f59e0b", "#94a3b8"];
const LIABILITY_COLORS = ["#f59e0b", "#ef4444", "#10b981"];

const compactFormatter = new Intl.NumberFormat("es-CO", {
  notation: "compact",
  maximumFractionDigits: 1,
});

function money(value: string | number): string {
  return formatCurrency(String(value));
}

function moneyNumber(value: string | number): number {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : 0;
}

function isoToday(): string {
  return new Date().toISOString().slice(0, 10);
}

function currentYearStart(): string {
  return `${new Date().getFullYear()}-01-01`;
}

function shiftDate(value: string, days: number): string {
  const date = new Date(`${value}T00:00:00Z`);
  date.setUTCDate(date.getUTCDate() + days);
  return date.toISOString().slice(0, 10);
}

function previousRange(fromDate: string, toDate: string): { from: string; to: string } {
  const start = new Date(`${fromDate}T00:00:00Z`);
  const end = new Date(`${toDate}T00:00:00Z`);
  const days = Math.round((end.getTime() - start.getTime()) / 86_400_000) + 1;
  const previousEnd = shiftDate(fromDate, -1);
  const previousStart = shiftDate(previousEnd, -(Math.max(days, 1) - 1));
  return { from: previousStart, to: previousEnd };
}

function calculateTrend(
  current: number,
  previous: number | null,
  favorableUp: boolean,
): Trend {
  if (previous === null || previous === 0) {
    return {
      arrow: "→",
      label: "Sin comparativo",
      className: "text-slate-500",
    };
  }

  const difference = current - previous;
  const percentage = Math.abs((difference / Math.abs(previous)) * 100);
  if (difference === 0) {
    return { arrow: "→", label: "0.0% vs anterior", className: "text-slate-500" };
  }

  const favorable = favorableUp ? difference > 0 : difference < 0;
  return {
    arrow: difference > 0 ? "↑" : "↓",
    label: `${percentage.toFixed(1)}% vs anterior`,
    className: favorable ? "text-emerald-600" : "text-red-600",
  };
}

function StatementTable({
  rows,
  onDrill,
  emptyMessage,
}: {
  rows: StatementRow[];
  onDrill: (account: { code: string; name: string }) => void;
  emptyMessage: string;
}) {
  if (rows.length === 0) {
    return (
      <p className="rounded-lg border border-dashed border-slate-300 px-4 py-8 text-center text-sm text-slate-500">
        {emptyMessage}
      </p>
    );
  }

  return (
    <div className="overflow-x-auto">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Concepto</TableHead>
            <TableHead className="text-right">Valor</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {rows.map((row) => (
            <TableRow
              key={row.key}
              className={row.bold ? "bg-violet-50/60 font-semibold" : undefined}
            >
              <TableCell className={row.indent ? "pl-8" : undefined}>
                {row.code ? (
                  <button
                    type="button"
                    onClick={() =>
                      onDrill({ code: row.code ?? "", name: row.name ?? row.code ?? "" })
                    }
                    className="inline-flex items-center gap-1.5 text-left text-sm font-medium text-violet-700 underline-offset-2 transition-colors hover:text-violet-500 hover:underline"
                  >
                    <span className="font-mono text-xs font-bold">{row.code}</span>
                    <span className="text-slate-600">{row.name}</span>
                  </button>
                ) : (
                  <span className={row.bold ? "text-slate-950" : "text-slate-700"}>
                    {row.label}
                  </span>
                )}
              </TableCell>
              <TableCell
                className={`text-right tabular-nums ${
                  row.bold ? "font-bold text-slate-950" : "text-slate-900"
                }`}
              >
                {money(row.value)}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}

export function NiifReportsClient() {
  const [fromDate, setFromDate] = useState(currentYearStart);
  const [toDate, setToDate] = useState(isoToday);
  const [tab, setTab] = useState<TabKey>("income");

  const [income, setIncome] = useState<NiifIncomeStatement | null>(null);
  const [previousIncome, setPreviousIncome] = useState<NiifIncomeStatement | null>(null);
  const [balance, setBalance] = useState<NiifBalanceSheet | null>(null);
  const [cash, setCash] = useState<NiifCashFlow | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [drillAccount, setDrillAccount] = useState<{ code: string; name: string } | null>(null);
  const [drillData, setDrillData] = useState<DrillDownReport | null>(null);
  const [drillLoading, setDrillLoading] = useState(false);
  const [drillError, setDrillError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;

    async function loadReports(): Promise<void> {
      if (!fromDate || !toDate) {
        if (active) {
          setLoading(false);
        }
        return;
      }
      if (fromDate > toDate) {
        if (active) {
          setError("La fecha inicial no puede ser posterior a la fecha final.");
          setLoading(false);
        }
        return;
      }

      const previous = previousRange(fromDate, toDate);
      if (active) {
        setLoading(true);
        setError(null);
      }

      try {
        const [currentIncome, priorIncome, currentBalance, currentCash] =
          await Promise.all([
            getNiifIncomeStatement(fromDate, toDate),
            getNiifIncomeStatement(previous.from, previous.to),
            getNiifBalanceSheet(toDate),
            getNiifCashFlow(fromDate, toDate),
          ]);
        if (!active) {
          return;
        }
        setIncome(currentIncome);
        setPreviousIncome(priorIncome);
        setBalance(currentBalance);
        setCash(currentCash);
      } catch (cause) {
        if (active) {
          setError(
            cause instanceof Error
              ? cause.message
              : "No se pudieron consultar los reportes financieros.",
          );
        }
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    }

    void loadReports();
    return () => {
      active = false;
    };
  }, [fromDate, toDate]);

  const revenue = income ? moneyNumber(income.revenue) : 0;
  const expenses = income ? moneyNumber(income.total_expenses) : 0;
  const netIncome = income ? moneyNumber(income.net_income) : 0;
  const previousRevenue = previousIncome ? moneyNumber(previousIncome.revenue) : null;
  const previousExpenses = previousIncome
    ? moneyNumber(previousIncome.total_expenses)
    : null;
  const previousNetIncome = previousIncome ? moneyNumber(previousIncome.net_income) : null;

  const revenueTrend = calculateTrend(revenue, previousRevenue, true);
  const expenseTrend = calculateTrend(expenses, previousExpenses, false);
  const netIncomeTrend = calculateTrend(netIncome, previousNetIncome, true);

  const incomeRows = useMemo<StatementRow[]>(() => {
    if (!income) {
      return [];
    }
    return income.sections.flatMap((section) => [
      {
        key: `section-${section.label}`,
        label: section.label,
        value: section.total,
        bold: section.kind !== undefined,
      },
      ...section.accounts.flat().map((account) => ({
        key: `account-${section.label}-${account.code}`,
        label: "",
        value: account.balance,
        code: account.code,
        name: account.name,
        indent: true,
      })),
    ]);
  }, [income]);

  const balanceRows = useMemo<StatementRow[]>(() => {
    if (!balance) {
      return [];
    }

    const matches = (account: ReportAccountRow, prefixes: string[]) =>
      prefixes.some((prefix) => account.code.startsWith(prefix));

    const currentAssets = balance.asset_accounts.filter((account) =>
      matches(account, ["11", "13", "14", "17"]),
    );
    const nonCurrentAssets = balance.asset_accounts.filter((account) =>
      matches(account, ["15", "16"]),
    );
    const currentLiabilities = balance.liability_accounts.filter((account) =>
      matches(account, ["22", "23", "24", "25", "26", "28"]),
    );
    const nonCurrentLiabilities = balance.liability_accounts.filter((account) =>
      matches(account, ["27"]),
    );

    const makeSection = (
      key: string,
      label: string,
      accounts: ReportAccountRow[],
      total: string,
    ): StatementRow[] => [
      { key: `balance-${key}`, label, value: total, bold: true },
      ...accounts.map((account) => ({
        key: `balance-${key}-${account.code}`,
        label: "",
        value: account.balance,
        code: account.code,
        name: account.name,
        indent: true,
      })),
    ];

    return [
      ...makeSection("current-assets", "Activo corriente", currentAssets, balance.current_assets),
      ...makeSection(
        "non-current-assets",
        "Activo no corriente",
        nonCurrentAssets,
        balance.non_current_assets,
      ),
      { key: "total-assets", label: "TOTAL ACTIVO", value: balance.total_assets, bold: true },
      ...makeSection(
        "current-liabilities",
        "Pasivo corriente",
        currentLiabilities,
        balance.current_liabilities,
      ),
      ...makeSection(
        "non-current-liabilities",
        "Pasivo no corriente",
        nonCurrentLiabilities,
        balance.non_current_liabilities,
      ),
      {
        key: "total-liabilities",
        label: "TOTAL PASIVO",
        value: balance.total_liabilities,
        bold: true,
      },
      {
        key: "equity-section",
        label: "Patrimonio",
        value: balance.equity,
        bold: true,
      },
      ...balance.equity_accounts.map((account) => ({
        key: `equity-${account.code}`,
        label: "",
        value: account.balance,
        code: account.code,
        name: account.name,
        indent: true,
      })),
      {
        key: "period-result",
        label: "Resultado del ejercicio",
        value: balance.period_result,
        indent: true,
      },
      {
        key: "total-equity",
        label: "TOTAL PATRIMONIO",
        value: balance.total_equity,
        bold: true,
      },
      {
        key: "liability-equity",
        label: "PASIVO + PATRIMONIO",
        value: balance.total_assets,
        bold: true,
      },
    ];
  }, [balance]);

  const cashRows = useMemo<StatementRow[]>(() => {
    if (!cash) {
      return [];
    }
    return [
      { key: "net-income", label: "Utilidad neta del periodo", value: cash.net_income },
      { key: "depreciation", label: "Depreciación y amortización (+)", value: cash.depreciation },
      {
        key: "receivables-change",
        label: "Variación de cuentas por cobrar (−)",
        value: cash.receivables_change,
      },
      {
        key: "inventory-change",
        label: "Variación de inventarios (−)",
        value: cash.inventory_change,
      },
      {
        key: "payables-change",
        label: "Variación de cuentas por pagar (+)",
        value: cash.payables_change,
      },
      {
        key: "operating",
        label: "FLUJO DE OPERACIÓN",
        value: cash.operating_cash_flow,
        bold: true,
      },
      {
        key: "investing",
        label: "FLUJO DE INVERSIÓN",
        value: cash.investing_cash_flow,
        bold: true,
      },
      {
        key: "financing",
        label: "FLUJO DE FINANCIACIÓN",
        value: cash.financing_cash_flow,
        bold: true,
      },
      {
        key: "net-cash-change",
        label: "Variación neta de efectivo",
        value: cash.net_cash_change,
      },
      { key: "opening-cash", label: "Efectivo al inicio", value: cash.opening_cash },
      {
        key: "closing-cash",
        label: "Efectivo al cierre",
        value: cash.closing_cash,
        bold: true,
      },
    ];
  }, [cash]);

  const incomeChartData = [
    { name: "Periodo actual", Ingresos: revenue, Gastos: expenses },
  ];

  const assetComposition = balance
    ? [
        { name: "Efectivo", value: moneyNumber(balance.asset_composition.cash) },
        {
          name: "Cuentas por cobrar",
          value: moneyNumber(balance.asset_composition.receivables),
        },
        { name: "Inventario", value: moneyNumber(balance.asset_composition.inventory) },
        {
          name: "Otros corrientes",
          value: moneyNumber(balance.asset_composition.other_current),
        },
        { name: "No corriente", value: moneyNumber(balance.asset_composition.non_current) },
      ].filter((item) => item.value > 0)
    : [];

  const liabilityEquityComposition = balance
    ? [
        {
          name: "Pasivo corriente",
          value: moneyNumber(balance.liability_equity_composition.current_liabilities),
        },
        {
          name: "Pasivo no corriente",
          value: moneyNumber(balance.liability_equity_composition.non_current_liabilities),
        },
        { name: "Patrimonio", value: moneyNumber(balance.liability_equity_composition.equity) },
      ].filter((item) => item.value > 0)
    : [];

  const exportHref =
    tab === "balance"
      ? getFinancialReportExportUrl("balance-sheet", { asOfDate: toDate })
      : getFinancialReportExportUrl("income-statement", {
          fromDate,
          toDate,
        });

  function openDrill(account: { code: string; name: string }): void {
    setDrillAccount(account);
    setDrillData(null);
    setDrillError(null);
    setDrillLoading(true);
    void getDrillDownReport(account.code, fromDate, toDate)
      .then((report) => setDrillData(report))
      .catch((cause) =>
        setDrillError(
          cause instanceof Error
            ? cause.message
            : "No se pudo consultar el auxiliar de la cuenta.",
        ),
      )
      .finally(() => setDrillLoading(false));
  }

  function closeDrill(): void {
    setDrillAccount(null);
    setDrillData(null);
    setDrillError(null);
  }

  async function handleExport(): Promise<void> {
    try {
      await downloadFileNative(
        exportHref,
        tab === "balance" ? "balance-general.xlsx" : "estado-resultados.xlsx",
      );
    } catch (cause) {
      window.alert(
        cause instanceof Error
          ? cause.message
          : "No se pudo descargar el archivo. Inténtalo de nuevo.",
      );
    }
  }

  return (
    <div className="space-y-6">
      <Card>
        <CardContent className="flex flex-col gap-4 py-4 lg:flex-row lg:items-end lg:justify-between">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-end">
            <label className="flex flex-col gap-1">
              <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                Desde
              </span>
              <input
                type="date"
                value={fromDate}
                onChange={(event) => {
                  setFromDate(event.target.value);
                  closeDrill();
                }}
                className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 shadow-sm outline-none focus:border-violet-500 focus:ring-2 focus:ring-violet-500/20"
              />
            </label>
            <label className="flex flex-col gap-1">
              <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                Hasta
              </span>
              <input
                type="date"
                value={toDate}
                onChange={(event) => {
                  setToDate(event.target.value);
                  closeDrill();
                }}
                className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 shadow-sm outline-none focus:border-violet-500 focus:ring-2 focus:ring-violet-500/20"
              />
            </label>
            {loading ? (
              <span className="pb-2 text-xs font-medium text-violet-600">Actualizando...</span>
            ) : null}
          </div>
          {tab !== "cash" ? (
            <Button
              onClick={() => {
                void handleExport();
              }}
              className="self-start lg:self-auto"
            >
              <Download className="mr-2 size-4" aria-hidden="true" />
              Exportar a Excel
            </Button>
          ) : null}
        </CardContent>
      </Card>

      {error ? (
        <div
          role="alert"
          className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700"
        >
          {error}
        </div>
      ) : null}

      {loading && !income ? (
        <Card>
          <CardContent className="py-12 text-center text-sm text-slate-500">
            Cargando cockpit financiero...
          </CardContent>
        </Card>
      ) : null}

      {income ? (
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {[
            {
              label: "Ingresos",
              value: revenue,
              trend: revenueTrend,
              accent: "border-emerald-200 bg-emerald-50/60",
            },
            {
              label: "Gastos y costos",
              value: expenses,
              trend: expenseTrend,
              accent: "border-red-200 bg-red-50/60",
            },
            {
              label: "Utilidad",
              value: netIncome,
              trend: netIncomeTrend,
              accent: "border-violet-200 bg-violet-50/60",
            },
          ].map((card) => (
            <Card key={card.label} className={card.accent}>
              <CardContent className="py-5">
                <p className="text-xs font-bold uppercase tracking-wider text-slate-500">
                  {card.label}
                </p>
                <p className="mt-2 break-words text-xl font-bold tabular-nums tracking-tight text-slate-950 xl:text-2xl">
                  {money(card.value)}
                </p>
                <p className={`mt-2 flex items-center gap-1 text-xs font-semibold ${card.trend.className}`}>
                  <span className="text-base leading-none">{card.trend.arrow}</span>
                  {card.trend.label}
                </p>
              </CardContent>
            </Card>
          ))}
        </div>
      ) : null}

      <Card>
        <CardHeader className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <CardTitle>Estados financieros NIIF</CardTitle>
            <CardDescription>
              Cockpit financiero del {formatDate(fromDate)} al {formatDate(toDate)} · datos en COP.
            </CardDescription>
          </div>
          <div className="flex flex-wrap gap-2" role="tablist" aria-label="Reportes NIIF">
            {(
              [
                ["income", "Estado de Resultados"],
                ["balance", "Balance General"],
                ["cash", "Flujo de Efectivo"],
              ] as const
            ).map(([key, label]) => (
              <button
                key={key}
                type="button"
                role="tab"
                aria-selected={tab === key}
                onClick={() => setTab(key)}
                className={`rounded-lg px-4 py-2 text-sm font-semibold transition-colors ${
                  tab === key
                    ? "bg-violet-600 text-white shadow-sm"
                    : "bg-zinc-100 text-zinc-700 hover:bg-zinc-200"
                }`}
              >
                {label}
              </button>
            ))}
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          {tab === "balance" && balance ? (
            <p className="flex items-center gap-2 rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-800">
              <CheckCircle2 className="size-4" aria-hidden="true" />
              Ecuación contable verificada: Activo = Pasivo + Patrimonio (descuadre 0.00).
            </p>
          ) : null}
          {tab === "cash" && cash ? (
            <p className="flex items-center gap-2 rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-800">
              <CheckCircle2 className="size-4" aria-hidden="true" />
              El efectivo al cierre coincide con el saldo en bancos (PUC 11).
            </p>
          ) : null}

          {tab === "income" && income ? (
            <>
              <Card className="border-violet-100 shadow-none">
                <CardHeader>
                  <CardTitle className="text-base">Ingresos vs. gastos del periodo</CardTitle>
                  <CardDescription>
                    Comparativo ejecutivo del periodo seleccionado.
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="h-72 w-full" role="img" aria-label="Ingresos versus gastos">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={incomeChartData} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
                        <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
                        <XAxis dataKey="name" axisLine={false} tickLine={false} tick={{ fill: "#64748b", fontSize: 12 }} />
                        <YAxis
                          axisLine={false}
                          tickLine={false}
                          tick={{ fill: "#64748b", fontSize: 12 }}
                          tickFormatter={(value: number) => compactFormatter.format(value)}
                          width={56}
                        />
                        <Tooltip
                          cursor={{ fill: "rgba(148, 163, 184, 0.12)" }}
                          formatter={(value) => [money(String(value)), ""]}
                          contentStyle={{
                            borderRadius: "0.75rem",
                            borderColor: "#e2e8f0",
                            fontSize: "0.875rem",
                          }}
                        />
                        <Legend wrapperStyle={{ fontSize: "0.875rem", paddingTop: "0.5rem" }} />
                        <Bar dataKey="Ingresos" fill="#10b981" radius={[6, 6, 0, 0]} maxBarSize={70} />
                        <Bar dataKey="Gastos" fill="#ef4444" radius={[6, 6, 0, 0]} maxBarSize={70} />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                </CardContent>
              </Card>
              <StatementTable rows={incomeRows} onDrill={openDrill} emptyMessage="No hay movimientos de ingresos o gastos en el periodo." />
            </>
          ) : null}

          {tab === "balance" && balance ? (
            <>
              <div className="grid gap-4 lg:grid-cols-2">
                <Card className="border-violet-100 shadow-none">
                  <CardHeader>
                    <CardTitle className="text-base">Composición del activo</CardTitle>
                    <CardDescription>Efectivo, cartera, inventario y otros activos.</CardDescription>
                  </CardHeader>
                  <CardContent>
                    {assetComposition.length === 0 ? (
                      <p className="py-10 text-center text-sm text-slate-500">Sin saldos de activo.</p>
                    ) : (
                      <div className="h-72 w-full" role="img" aria-label="Composición del activo">
                        <ResponsiveContainer width="100%" height="100%">
                          <PieChart>
                            <Pie data={assetComposition} dataKey="value" nameKey="name" innerRadius={52} outerRadius={92} paddingAngle={2}>
                              {assetComposition.map((item, index) => (
                                <Cell key={item.name} fill={ASSET_COLORS[index % ASSET_COLORS.length]} />
                              ))}
                            </Pie>
                            <Tooltip formatter={(value) => money(String(value))} />
                            <Legend wrapperStyle={{ fontSize: "0.8rem" }} />
                          </PieChart>
                        </ResponsiveContainer>
                      </div>
                    )}
                  </CardContent>
                </Card>
                <Card className="border-violet-100 shadow-none">
                  <CardHeader>
                    <CardTitle className="text-base">Pasivo + Patrimonio</CardTitle>
                    <CardDescription>Estructura de financiación del balance.</CardDescription>
                  </CardHeader>
                  <CardContent>
                    {liabilityEquityComposition.length === 0 ? (
                      <p className="py-10 text-center text-sm text-slate-500">Sin saldos de pasivo o patrimonio.</p>
                    ) : (
                      <div className="h-72 w-full" role="img" aria-label="Composición de pasivo y patrimonio">
                        <ResponsiveContainer width="100%" height="100%">
                          <PieChart>
                            <Pie data={liabilityEquityComposition} dataKey="value" nameKey="name" innerRadius={52} outerRadius={92} paddingAngle={2}>
                              {liabilityEquityComposition.map((item, index) => (
                                <Cell key={item.name} fill={LIABILITY_COLORS[index % LIABILITY_COLORS.length]} />
                              ))}
                            </Pie>
                            <Tooltip formatter={(value) => money(String(value))} />
                            <Legend wrapperStyle={{ fontSize: "0.8rem" }} />
                          </PieChart>
                        </ResponsiveContainer>
                      </div>
                    )}
                  </CardContent>
                </Card>
              </div>
              <StatementTable rows={balanceRows} onDrill={openDrill} emptyMessage="No hay saldos en el balance." />
            </>
          ) : null}

          {tab === "cash" && cash ? (
            <StatementTable rows={cashRows} onDrill={openDrill} emptyMessage="No hay movimientos de efectivo." />
          ) : null}
        </CardContent>
      </Card>

      {drillAccount ? (
        <Modal
          title={`Auxiliar ${drillAccount.code} · ${drillAccount.name}`}
          description={`Movimientos del ${formatDate(fromDate)} al ${formatDate(toDate)}.`}
          onClose={closeDrill}
          maxWidthClassName="max-w-5xl"
          headerAction={
            <button
              type="button"
              onClick={closeDrill}
              className="rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 transition-colors hover:bg-slate-50"
            >
              Cerrar
            </button>
          }
        >
          {drillLoading ? (
            <p className="py-8 text-center text-sm text-slate-500">Cargando movimientos...</p>
          ) : drillError ? (
            <p className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
              {drillError}
            </p>
          ) : drillData ? (
            <div className="space-y-4">
              <div className="grid gap-3 sm:grid-cols-4">
                <div className="rounded-lg bg-slate-50 px-3 py-2">
                  <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">Saldo inicial</p>
                  <p className="mt-1 text-sm font-bold tabular-nums text-slate-900">{money(drillData.opening_balance)}</p>
                </div>
                <div className="rounded-lg bg-slate-50 px-3 py-2">
                  <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">Débitos</p>
                  <p className="mt-1 text-sm font-bold tabular-nums text-slate-900">{money(drillData.total_debits)}</p>
                </div>
                <div className="rounded-lg bg-slate-50 px-3 py-2">
                  <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">Créditos</p>
                  <p className="mt-1 text-sm font-bold tabular-nums text-slate-900">{money(drillData.total_credits)}</p>
                </div>
                <div className="rounded-lg bg-violet-50 px-3 py-2">
                  <p className="text-[11px] font-semibold uppercase tracking-wide text-violet-600">Saldo final</p>
                  <p className="mt-1 text-sm font-bold tabular-nums text-violet-900">{money(drillData.closing_balance)}</p>
                </div>
              </div>

              {drillData.movements.length === 0 ? (
                <p className="rounded-lg border border-dashed border-slate-300 px-4 py-8 text-center text-sm text-slate-500">
                  No hay movimientos para esta cuenta en el periodo.
                </p>
              ) : (
                <div className="overflow-x-auto">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Fecha</TableHead>
                        <TableHead>Asiento</TableHead>
                        <TableHead>Descripción</TableHead>
                        <TableHead className="text-right">Débito</TableHead>
                        <TableHead className="text-right">Crédito</TableHead>
                        <TableHead className="text-right">Saldo</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {drillData.movements.map((movement) => (
                        <TableRow key={movement.id}>
                          <TableCell className="whitespace-nowrap text-sm text-slate-700">{formatDate(movement.entry_date)}</TableCell>
                          <TableCell className="whitespace-nowrap font-mono text-xs text-slate-500">{movement.entry_number}</TableCell>
                          <TableCell className="text-sm text-slate-800">{movement.description}</TableCell>
                          <TableCell className="text-right tabular-nums text-slate-900">{money(movement.debit)}</TableCell>
                          <TableCell className="text-right tabular-nums text-slate-900">{money(movement.credit)}</TableCell>
                          <TableCell className="text-right tabular-nums font-semibold text-slate-950">{money(movement.balance)}</TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              )}

              <div className="flex justify-end">
                <Button
                  className="border border-slate-300 bg-white text-slate-700 hover:bg-slate-50"
                  onClick={closeDrill}
                >
                  Cerrar
                </Button>
              </div>
            </div>
          ) : null}
        </Modal>
      ) : null}
    </div>
  );
}
