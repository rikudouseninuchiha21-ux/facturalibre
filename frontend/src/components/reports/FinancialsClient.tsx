"use client";

import { useState } from "react";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  type BalanceSheetResponse,
  type IncomeStatementResponse,
} from "@/lib/api";
import { formatCurrency } from "@/lib/format";

const money = (value: string): string =>
  formatCurrency(value, "COP");

const tabStyles =
  "inline-flex items-center justify-center rounded-lg px-4 py-2 text-sm font-semibold transition-colors hover:bg-slate-100 focus-visible:outline-2 focus-visible:outline-offset-2";

const tabActive = "bg-slate-900 text-white";
const tabInactive = "text-slate-600 hover:text-slate-950";

interface FinancialsClientProps {
  incomeStatement: IncomeStatementResponse;
  balanceSheet: BalanceSheetResponse;
}

export function FinancialsClient({
  incomeStatement,
  balanceSheet,
}: FinancialsClientProps) {
  const [tab, setTab] = useState<"income" | "balance">("income");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [asOfDate, setAsOfDate] = useState("");

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap gap-2">
        <button
          onClick={() => setTab("income")}
          className={`${tabStyles} ${
            tab === "income" ? tabActive : tabInactive
          }`}
        >
          Estado de Resultados
        </button>
        <button
          onClick={() => setTab("balance")}
          className={`${tabStyles} ${
            tab === "balance" ? tabActive : tabInactive
          }`}
        >
          Balance General
        </button>
      </div>

      {tab === "income" ? (
        <IncomeStatementView
          data={incomeStatement}
          startDate={startDate}
          endDate={endDate}
          onStartDateChange={setStartDate}
          onEndDateChange={setEndDate}
        />
      ) : (
        <BalanceSheetView
          data={balanceSheet}
          asOfDate={asOfDate}
          onAsOfDateChange={setAsOfDate}
        />
      )}
    </div>
  );
}

function IncomeStatementView({
  data,
  startDate,
  endDate,
  onStartDateChange,
  onEndDateChange,
}: {
  data: IncomeStatementResponse;
  startDate: string;
  endDate: string;
  onStartDateChange: (value: string) => void;
  onEndDateChange: (value: string) => void;
}) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Estado de Resultados</CardTitle>
        <CardDescription>
          Ingresos, gastos y utilidad neta del período seleccionado.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        <div className="flex flex-wrap items-end gap-4">
          <div>
            <label htmlFor="is-start-date" className="text-xs font-medium text-slate-500">
              Desde
            </label>
            <input
              id="is-start-date"
              type="date"
              value={startDate}
              onChange={(e) => onStartDateChange(e.target.value)}
              className="mt-1 block w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-950 shadow-sm outline-none transition focus:border-slate-900 focus:ring-2 focus:ring-slate-900/10"
            />
          </div>
          <div>
            <label htmlFor="is-end-date" className="text-xs font-medium text-slate-500">
              Hasta
            </label>
            <input
              id="is-end-date"
              type="date"
              value={endDate}
              onChange={(e) => onEndDateChange(e.target.value)}
              className="mt-1 block w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-950 shadow-sm outline-none transition focus:border-slate-900 focus:ring-2 focus:ring-slate-900/10"
            />
          </div>
        </div>

        <div className="grid grid-cols-2 gap-8">
          <div>
            <h3 className="text-sm font-semibold text-slate-700 mb-4">
              Ingresos
            </h3>
            <div className="space-y-3">
              {data.income_accounts.map((acct) => (
                <div
                  key={acct.code}
                  className="flex justify-between text-sm"
                >
                  <span className="text-slate-600">{acct.code}</span>
                  <span className="text-slate-900">{acct.name}</span>
                  <span className="tabular-nums font-medium text-slate-900">
                    {money(acct.balance)}
                  </span>
                </div>
              ))}
              <div className="mt-2 pt-2 border-t border-slate-200 flex justify-between text-sm font-semibold text-slate-950">
                <span>Total Ingresos</span>
                <span>{money(data.total_income)}</span>
              </div>
            </div>
          </div>

          <div>
            <h3 className="text-sm font-semibold text-slate-700 mb-4">
              Gastos
            </h3>
            <div className="space-y-3">
              {data.expense_accounts.map((acct) => (
                <div
                  key={acct.code}
                  className="flex justify-between text-sm"
                >
                  <span className="text-slate-600">{acct.code}</span>
                  <span className="text-slate-900">{acct.name}</span>
                  <span className="tabular-nums font-medium text-slate-900">
                    {money(acct.balance)}
                  </span>
                </div>
              ))}
              <div className="mt-2 pt-2 border-t border-slate-200 flex justify-between text-sm font-semibold text-slate-950">
                <span>Total Gastos</span>
                <span>{money(data.total_expenses)}</span>
              </div>
            </div>
          </div>
        </div>

        <div className="bg-slate-50 rounded-xl p-4">
          <div className="flex justify-between text-lg font-bold text-slate-950">
            <span>Utilidad Neta</span>
            <span>{money(data.net_income)}</span>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

function BalanceSheetView({
  data,
  asOfDate,
  onAsOfDateChange,
}: {
  data: BalanceSheetResponse;
  asOfDate: string;
  onAsOfDateChange: (value: string) => void;
}) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Balance General</CardTitle>
        <CardDescription>
          Activos, pasivos y patrimonio a la fecha de corte seleccionada.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        <div className="flex items-end gap-4">
          <div>
            <label htmlFor="bs-date" className="text-xs font-medium text-slate-500">
              Fecha de corte
            </label>
            <input
              id="bs-date"
              type="date"
              value={asOfDate}
              onChange={(e) => onAsOfDateChange(e.target.value)}
              className="mt-1 block w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-950 shadow-sm outline-none transition focus:border-slate-900 focus:ring-2 focus:ring-slate-900/10"
            />
          </div>
          <div className="ml-auto">
            <button
              type="button"
              className={`inline-flex items-center justify-center rounded-lg border px-3 py-1 text-sm font-semibold transition-colors hover:bg-slate-50 ${
                data.balanced
                  ? "border-emerald-200 text-emerald-600 hover:border-emerald-300 hover:bg-emerald-50"
                  : "border-red-200 text-red-600 hover:border-red-300 hover:bg-red-50"
              }`}
            >
              {data.balanced ? "Balance cuadrado" : "Balance no cuadrado"}
            </button>
          </div>
        </div>

        <div className="grid grid-cols-3 gap-8">
          <div>
            <h3 className="text-sm font-semibold text-slate-700 mb-4">
              Activos
            </h3>
            <div className="space-y-3">
              {data.asset_accounts.map((acct) => (
                <div
                  key={acct.code}
                  className="flex justify-between text-sm"
                >
                  <span className="text-slate-600">{acct.code}</span>
                  <span className="text-slate-900">{acct.name}</span>
                  <span className="tabular-nums font-medium text-slate-900">
                    {money(acct.balance)}
                  </span>
                </div>
              ))}
              <div className="mt-2 pt-2 border-t border-slate-200 flex justify-between text-sm font-semibold text-slate-950">
                <span>Total Activos</span>
                <span>{money(data.total_assets)}</span>
              </div>
            </div>
          </div>

          <div>
            <h3 className="text-sm font-semibold text-slate-700 mb-4">
              Pasivos
            </h3>
            <div className="space-y-3">
              {data.liability_accounts.map((acct) => (
                <div
                  key={acct.code}
                  className="flex justify-between text-sm"
                >
                  <span className="text-slate-600">{acct.code}</span>
                  <span className="text-slate-900">{acct.name}</span>
                  <span className="tabular-nums font-medium text-slate-900">
                    {money(acct.balance)}
                  </span>
                </div>
              ))}
              <div className="mt-2 pt-2 border-t border-slate-200 flex justify-between text-sm font-semibold text-slate-950">
                <span>Total Pasivos</span>
                <span>{money(data.total_liabilities)}</span>
              </div>
            </div>
          </div>

          <div>
            <h3 className="text-sm font-semibold text-slate-700 mb-4">
              Patrimonio
            </h3>
            <div className="space-y-3">
              {data.equity_accounts.map((acct) => (
                <div
                  key={acct.code}
                  className="flex justify-between text-sm"
                >
                  <span className="text-slate-600">{acct.code}</span>
                  <span className="text-slate-900">{acct.name}</span>
                  <span className="tabular-nums font-medium text-slate-900">
                    {money(acct.balance)}
                  </span>
                </div>
              ))}
              <div className="mt-2 pt-2 border-t border-slate-200 flex justify-between text-sm font-semibold text-slate-950">
                <span>Total Patrimonio</span>
                <span>{money(data.total_equity)}</span>
              </div>
            </div>
          </div>
        </div>

        <div className="bg-slate-50 rounded-xl p-4">
          <div className="flex justify-between text-lg font-bold text-slate-950">
            <span>Activo = Pasivo + Patrimonio</span>
            <span className={`text-lg font-bold ${
              data.balanced ? "text-emerald-600" : "text-red-600"
            }`}>
              {data.balanced ? "✓ Cuadrado" : "✗ No cuadrado"}
            </span>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
