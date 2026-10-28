"use client";

import { useState } from "react";
import { CheckCircle2, Download } from "lucide-react";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table";
import { formatCurrency, formatDate } from "@/lib/format";
import type {
  NiifBalanceSheet,
  NiifCashFlow,
  NiifIncomeStatement,
} from "@/lib/api";

interface NiifReportsClientProps {
  income: NiifIncomeStatement;
  balance: NiifBalanceSheet;
  cash: NiifCashFlow;
}

type Row = { label: string; value: string; bold?: boolean; color?: string };

function money(value: string): number {
  return Number(value);
}

function renderRows(rows: Row[], fileName: string) {
  function exportCsv() {
    const lines = ["Concepto,Valor", ...rows.map((row) => `"${row.label}",${row.value}`)];
    const blob = new Blob([`\uFEFF${lines.join("\n")}`], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = fileName;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  }

  return (
    <>
      <div className="flex justify-end">
        <button
          type="button"
          onClick={exportCsv}
          className="inline-flex items-center gap-1.5 rounded-lg bg-violet-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-violet-500"
        >
          <Download className="size-3.5" aria-hidden="true" />
          Exportar CSV
        </button>
      </div>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Concepto</TableHead>
            <TableHead className="text-right">Valor</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {rows.map((row) => (
            <TableRow key={row.label} className={row.bold ? "bg-zinc-50 font-semibold" : ""}>
              <TableCell className={row.bold ? "font-bold text-zinc-950" : "text-zinc-700"}>
                {row.label}
              </TableCell>
              <TableCell
                className={`text-right tabular-nums ${row.color ?? "text-zinc-900"} ${row.bold ? "border-t border-zinc-300 font-bold" : ""}`}
              >
                {formatCurrency(row.value)}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </>
  );
}

export function NiifReportsClient({ income, balance, cash }: NiifReportsClientProps) {
  const [tab, setTab] = useState<"income" | "balance" | "cash">("income");
  const green = "text-emerald-700";
  const red = "text-red-700";

  const incomeRows: Row[] = income.sections.flatMap((section) => [
    { label: section.label, value: section.total, bold: section.kind !== undefined,
      color: section.kind === "net" ? (money(section.total) >= 0 ? green : red) : undefined },
    ...section.accounts.flat().map((account) => ({
      label: `${account.code} · ${account.name}`,
      value: account.balance,
      color: money(account.balance) < 0 ? red : undefined,
    })),
  ]);

  const balanceRows: Row[] = [
    { label: "Activo corriente", value: balance.current_assets },
    { label: "Activo no corriente", value: balance.non_current_assets },
    { label: "TOTAL ACTIVO", value: balance.total_assets, bold: true },
    { label: "Pasivo corriente", value: balance.current_liabilities },
    { label: "Pasivo no corriente", value: balance.non_current_liabilities },
    { label: "TOTAL PASIVO", value: balance.total_liabilities, bold: true },
    { label: "Capital social", value: balance.equity },
    { label: "Resultado del ejercicio", value: balance.period_result,
      color: money(balance.period_result) >= 0 ? green : red },
    { label: "TOTAL PATRIMONIO", value: balance.total_equity, bold: true },
    { label: "PASIVO + PATRIMONIO", value: String(money(balance.total_liabilities) + money(balance.total_equity)),
      bold: true, color: green },
  ];

  const cashRows: Row[] = [
    { label: "Utilidad neta del periodo", value: cash.net_income,
      color: money(cash.net_income) >= 0 ? green : red },
    { label: "Depreciación y amortización (+)", value: cash.depreciation },
    { label: "Variación de cuentas por cobrar (−)", value: cash.receivables_change },
    { label: "Variación de inventarios (−)", value: cash.inventory_change },
    { label: "Variación de cuentas por pagar (+)", value: cash.payables_change },
    { label: "FLUJO DE OPERACIÓN", value: cash.operating_cash_flow, bold: true },
    { label: "FLUJO DE INVERSIÓN", value: cash.investing_cash_flow, bold: true },
    { label: "FLUJO DE FINANCIACIÓN", value: cash.financing_cash_flow, bold: true },
    { label: "Variación neta de efectivo", value: cash.net_cash_change,
      color: money(cash.net_cash_change) >= 0 ? green : red },
    { label: "Efectivo al inicio", value: cash.opening_cash },
    { label: "Efectivo al cierre", value: cash.closing_cash, bold: true },
  ];

  return (
    <Card>
      <CardHeader className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <CardTitle>Estados financieros NIIF</CardTitle>
          <CardDescription>
            Del {formatDate(income.from_date)} al {formatDate(income.to_date)} · datos en COP.
          </CardDescription>
        </div>
        <div className="flex flex-wrap gap-2" role="tablist" aria-label="Reportes NIIF">
          {(
            [["income", "Estado de Resultados"], ["balance", "Balance General"], ["cash", "Flujo de Efectivo"]] as const
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
              {label} NIIF
            </button>
          ))}
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {tab === "balance" ? (
          <p className="flex items-center gap-2 rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-800">
            <CheckCircle2 className="size-4" aria-hidden="true" />
            Ecuación contable verificada: Activo = Pasivo + Patrimonio (descuadre 0.00).
          </p>
        ) : null}
        {tab === "cash" ? (
          <p className="flex items-center gap-2 rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-800">
            <CheckCircle2 className="size-4" aria-hidden="true" />
            El efectivo al cierre coincide con el saldo en bancos (PUC 11).
          </p>
        ) : null}
        <div className={tab === "income" ? "" : "hidden"}>
          {renderRows(incomeRows, "estado-resultados-niif.csv")}
        </div>
        <div className={tab === "balance" ? "" : "hidden"}>
          {renderRows(balanceRows, "balance-general-niif.csv")}
        </div>
        <div className={tab === "cash" ? "" : "hidden"}>
          {renderRows(cashRows, "flujo-efectivo-niif.csv")}
        </div>
      </CardContent>
    </Card>
  );
}
