"use client";

import { useEffect, useState } from "react";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  type AccountingAccount,
  type BalanceSheetResponse,
  type IncomeStatementResponse,
  type LedgerReport,
  type TrialBalanceReport,
  closePeriod,
  getLedger,
  getTrialBalance,
} from "@/lib/api";
import { formatCurrency } from "@/lib/format";

const money = (value: string): string => formatCurrency(value, "COP");

const tabStyles =
  "inline-flex items-center justify-center rounded-lg px-4 py-2 text-sm font-semibold transition-colors hover:bg-slate-100 focus-visible:outline-2 focus-visible:outline-offset-2";

const tabActive = "bg-violet-600 text-white";
const tabInactive = "text-slate-600 hover:text-slate-950";

const inputStyles =
  "mt-1 block w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-950 shadow-sm outline-none transition focus:border-violet-500 focus:ring-2 focus:ring-violet-500/20";

type Tab = "income" | "balance" | "ledger" | "trial";

interface FinancialsClientProps {
  incomeStatement: IncomeStatementResponse;
  balanceSheet: BalanceSheetResponse;
  accounts: AccountingAccount[];
  isAdmin: boolean;
  initialStartDate: string;
  initialEndDate: string;
  initialAsOfDate: string;
}

export function FinancialsClient({
  incomeStatement,
  balanceSheet,
  accounts,
  isAdmin,
  initialStartDate,
  initialEndDate,
  initialAsOfDate,
}: FinancialsClientProps) {
  const [tab, setTab] = useState<Tab>("income");
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
        <button
          onClick={() => setTab("ledger")}
          className={`${tabStyles} ${
            tab === "ledger" ? tabActive : tabInactive
          }`}
        >
          Libro Mayor
        </button>
        <button
          onClick={() => setTab("trial")}
          className={`${tabStyles} ${
            tab === "trial" ? tabActive : tabInactive
          }`}
        >
          Balance de Prueba
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
      ) : tab === "balance" ? (
        <BalanceSheetView
          data={balanceSheet}
          asOfDate={asOfDate}
          onAsOfDateChange={setAsOfDate}
        />
      ) : tab === "ledger" ? (
        <LedgerView
          accounts={accounts}
          initialStartDate={initialStartDate}
          initialEndDate={initialEndDate}
        />
      ) : (
        <TrialBalanceView
          isAdmin={isAdmin}
          initialAsOfDate={initialAsOfDate}
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
              className={inputStyles}
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
              className={inputStyles}
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
              className={inputStyles}
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

function LedgerView({
  accounts,
  initialStartDate,
  initialEndDate,
}: {
  accounts: AccountingAccount[];
  initialStartDate: string;
  initialEndDate: string;
}) {
  const [accountQuery, setAccountQuery] = useState("");
  const [selectedCode, setSelectedCode] = useState("");
  const [startDate, setStartDate] = useState(initialStartDate);
  const [endDate, setEndDate] = useState(initialEndDate);
  const [report, setReport] = useState<LedgerReport | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const normalizedQuery = accountQuery.trim().toLowerCase();
  const matchingAccounts = accounts
    .filter(
      (account) =>
        normalizedQuery.length === 0 ||
        account.code.toLowerCase().includes(normalizedQuery) ||
        account.name.toLowerCase().includes(normalizedQuery),
    )
    .slice(0, 8);

  const selectAccount = (account: AccountingAccount) => {
    setSelectedCode(account.code);
    setAccountQuery(`${account.code} - ${account.name}`);
    setReport(null);
    setError(null);
  };

  const handleSearch = async () => {
    const typedCode = accountQuery.trim().split(" - ")[0];
    const resolvedCode =
      selectedCode ||
      accounts.find((account) => account.code === typedCode)?.code ||
      "";
    if (!resolvedCode) {
      setError("Selecciona una cuenta del catálogo para consultar el libro.");
      return;
    }
    setSelectedCode(resolvedCode);
    setLoading(true);
    setError(null);
    try {
      const data = await getLedger(resolvedCode, startDate, endDate);
      setReport(data);
    } catch (cause) {
      setReport(null);
      setError(
        cause instanceof Error
          ? cause.message
          : "No se pudo consultar el Libro Mayor.",
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Libro Mayor</CardTitle>
        <CardDescription>
          Movimientos débito y crédito de una cuenta, con saldo inicial y final.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        <div className="grid gap-4 md:grid-cols-[minmax(0,2fr)_minmax(0,1fr)_minmax(0,1fr)_auto] md:items-end">
          <div className="relative">
            <label htmlFor="ledger-account" className="text-xs font-medium text-slate-500">
              Cuenta contable
            </label>
            <input
              id="ledger-account"
              type="search"
              value={accountQuery}
              onChange={(event) => {
                setAccountQuery(event.target.value);
                setSelectedCode("");
                setReport(null);
              }}
              placeholder="Buscar por código o nombre"
              autoComplete="off"
              className={inputStyles}
            />
            {accountQuery.length > 0 && !selectedCode && matchingAccounts.length > 0 ? (
              <ul className="absolute z-20 mt-1 max-h-64 w-full overflow-y-auto rounded-lg border border-slate-200 bg-white py-1 shadow-lg">
                {matchingAccounts.map((account) => (
                  <li key={account.code}>
                    <button
                      type="button"
                      onClick={() => selectAccount(account)}
                      className="flex w-full items-center justify-between gap-3 px-3 py-2 text-left text-sm hover:bg-slate-50"
                    >
                      <span className="font-mono text-xs text-slate-500">
                        {account.code}
                      </span>
                      <span className="flex-1 text-slate-900">{account.name}</span>
                    </button>
                  </li>
                ))}
              </ul>
            ) : null}
          </div>

          <div>
            <label htmlFor="ledger-start" className="text-xs font-medium text-slate-500">
              Desde
            </label>
            <input
              id="ledger-start"
              type="date"
              value={startDate}
              onChange={(event) => setStartDate(event.target.value)}
              className={inputStyles}
            />
          </div>
          <div>
            <label htmlFor="ledger-end" className="text-xs font-medium text-slate-500">
              Hasta
            </label>
            <input
              id="ledger-end"
              type="date"
              value={endDate}
              onChange={(event) => setEndDate(event.target.value)}
              className={inputStyles}
            />
          </div>
          <button
            type="button"
            onClick={() => void handleSearch()}
            disabled={loading}
            className="inline-flex items-center justify-center rounded-lg bg-violet-600 px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-violet-500 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {loading ? "Consultando…" : "Consultar"}
          </button>
        </div>

        {error ? (
          <div
            role="alert"
            className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700"
          >
            {error}
          </div>
        ) : null}

        {report ? (
          <>
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              <SummaryTile label="Saldo inicial" value={report.opening_balance} />
              <SummaryTile label="Débitos" value={report.total_debits} />
              <SummaryTile label="Créditos" value={report.total_credits} />
              <SummaryTile label="Saldo final" value={report.closing_balance} />
            </div>

            <div className="overflow-x-auto rounded-xl border border-slate-200">
              <table className="min-w-full divide-y divide-slate-200 text-sm">
                <thead className="bg-slate-50">
                  <tr>
                    <th className="px-4 py-3 text-left font-semibold text-slate-600">
                      Fecha
                    </th>
                    <th className="px-4 py-3 text-left font-semibold text-slate-600">
                      Descripción
                    </th>
                    <th className="px-4 py-3 text-right font-semibold text-slate-600">
                      Débito
                    </th>
                    <th className="px-4 py-3 text-right font-semibold text-slate-600">
                      Crédito
                    </th>
                    <th className="px-4 py-3 text-right font-semibold text-slate-600">
                      Saldo
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  <tr className="bg-slate-50/60">
                    <td className="px-4 py-3 text-slate-500" colSpan={4}>
                      Saldo inicial al {report.start_date ?? "inicio"}
                    </td>
                    <td className="px-4 py-3 text-right font-semibold tabular-nums text-slate-900">
                      {money(report.opening_balance)}
                    </td>
                  </tr>
                  {report.movements.length === 0 ? (
                    <tr>
                      <td className="px-4 py-6 text-center text-slate-500" colSpan={5}>
                        No hay movimientos en el rango seleccionado.
                      </td>
                    </tr>
                  ) : (
                    report.movements.map((movement) => (
                      <tr key={movement.id} className="hover:bg-slate-50">
                        <td className="whitespace-nowrap px-4 py-3 text-slate-600">
                          {movement.entry_date}
                        </td>
                        <td className="px-4 py-3 text-slate-900">
                          {movement.description}
                        </td>
                        <td className="px-4 py-3 text-right tabular-nums text-slate-900">
                          {money(movement.debit)}
                        </td>
                        <td className="px-4 py-3 text-right tabular-nums text-slate-900">
                          {money(movement.credit)}
                        </td>
                        <td className="px-4 py-3 text-right font-medium tabular-nums text-slate-900">
                          {money(movement.balance)}
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </>
        ) : null}
      </CardContent>
    </Card>
  );
}

function SummaryTile({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-slate-50 px-4 py-3">
      <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
        {label}
      </p>
      <p className="mt-1 text-lg font-bold tabular-nums text-slate-950">
        {money(value)}
      </p>
    </div>
  );
}

function TrialBalanceView({
  isAdmin,
  initialAsOfDate,
}: {
  isAdmin: boolean;
  initialAsOfDate: string;
}) {
  const [asOfDate, setAsOfDate] = useState(initialAsOfDate);
  const [report, setReport] = useState<TrialBalanceReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [refreshKey, setRefreshKey] = useState(0);
  const [closeMonth, setCloseMonth] = useState(
    Number(initialAsOfDate.slice(5, 7)) || new Date().getMonth() + 1,
  );
  const [closeYear, setCloseYear] = useState(
    Number(initialAsOfDate.slice(0, 4)) || new Date().getFullYear(),
  );
  const [closing, setClosing] = useState(false);
  const [closeMessage, setCloseMessage] = useState<string | null>(null);
  const [closeError, setCloseError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    getTrialBalance(asOfDate)
      .then((data) => {
        if (!cancelled) setReport(data);
      })
      .catch((cause: unknown) => {
        if (!cancelled) {
          setReport(null);
          setError(
            cause instanceof Error
              ? cause.message
              : "No se pudo consultar el Balance de Prueba.",
          );
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [asOfDate, refreshKey]);

  const handleClosePeriod = async () => {
    setClosing(true);
    setCloseMessage(null);
    setCloseError(null);
    try {
      const period = await closePeriod(closeMonth, closeYear);
      setCloseMessage(
        `Periodo ${String(period.month).padStart(2, "0")}/${period.year} cerrado correctamente.`,
      );
      setLoading(true);
      setError(null);
      setRefreshKey((value) => value + 1);
    } catch (cause) {
      setCloseError(
        cause instanceof Error
          ? cause.message
          : "No se pudo cerrar el periodo.",
      );
    } finally {
      setClosing(false);
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Balance de Prueba</CardTitle>
        <CardDescription>
          Débitos, créditos y saldo de todas las cuentas a la fecha de corte.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        <div className="flex flex-wrap items-end gap-4">
          <div>
            <label htmlFor="trial-date" className="text-xs font-medium text-slate-500">
              Fecha de corte
            </label>
            <input
              id="trial-date"
              type="date"
              value={asOfDate}
              onChange={(event) => {
                setAsOfDate(event.target.value);
                setLoading(true);
                setError(null);
              }}
              className={inputStyles}
            />
          </div>
          {report ? (
            <div
              role="status"
              className={`ml-auto rounded-lg border px-3 py-1 text-sm font-semibold ${
                report.balanced
                  ? "border-emerald-200 bg-emerald-50 text-emerald-700"
                  : "border-red-200 bg-red-50 text-red-700"
              }`}
            >
              {report.balanced
                ? "✓ Débitos = Créditos"
                : `✗ Diferencia: ${money(report.difference)}`}
            </div>
          ) : null}
        </div>

        {error ? (
          <div
            role="alert"
            className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700"
          >
            {error}
          </div>
        ) : null}

        {loading ? (
          <p className="text-sm text-slate-500">Cargando Balance de Prueba…</p>
        ) : report ? (
          <div className="overflow-x-auto rounded-xl border border-slate-200">
            <table className="min-w-full divide-y divide-slate-200 text-sm">
              <thead className="bg-slate-50">
                <tr>
                  <th className="px-4 py-3 text-left font-semibold text-slate-600">
                    Código
                  </th>
                  <th className="px-4 py-3 text-left font-semibold text-slate-600">
                    Nombre
                  </th>
                  <th className="px-4 py-3 text-right font-semibold text-slate-600">
                    Débitos
                  </th>
                  <th className="px-4 py-3 text-right font-semibold text-slate-600">
                    Créditos
                  </th>
                  <th className="px-4 py-3 text-right font-semibold text-slate-600">
                    Saldo
                  </th>
                  <th className="px-4 py-3 text-left font-semibold text-slate-600">
                    Tipo
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {report.accounts.map((account) => (
                  <tr key={account.code} className="hover:bg-slate-50">
                    <td className="whitespace-nowrap px-4 py-3 font-mono text-xs text-slate-500">
                      {account.code}
                    </td>
                    <td className="px-4 py-3 text-slate-900">{account.name}</td>
                    <td className="px-4 py-3 text-right tabular-nums text-slate-900">
                      {money(account.debit)}
                    </td>
                    <td className="px-4 py-3 text-right tabular-nums text-slate-900">
                      {money(account.credit)}
                    </td>
                    <td className="px-4 py-3 text-right font-medium tabular-nums text-slate-900">
                      {money(account.balance)}
                    </td>
                    <td className="px-4 py-3">
                      <span
                        className={`inline-flex rounded-full px-2 py-0.5 text-xs font-semibold ${
                          account.balance_type === "DEUDOR"
                            ? "bg-sky-50 text-sky-700"
                            : account.balance_type === "ACREEDOR"
                              ? "bg-amber-50 text-amber-700"
                              : "bg-slate-100 text-slate-500"
                        }`}
                      >
                        {account.balance_type}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
              <tfoot className="bg-slate-50 font-semibold text-slate-950">
                <tr>
                  <td className="px-4 py-3" colSpan={2}>
                    Totales
                  </td>
                  <td className="px-4 py-3 text-right tabular-nums">
                    {money(report.total_debit)}
                  </td>
                  <td className="px-4 py-3 text-right tabular-nums">
                    {money(report.total_credit)}
                  </td>
                  <td className="px-4 py-3 text-right tabular-nums" colSpan={2}>
                    {money(report.difference)}
                  </td>
                </tr>
              </tfoot>
            </table>
          </div>
        ) : null}

        {isAdmin ? (
          <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
            <div className="flex flex-wrap items-end gap-3">
              <div>
                <h3 className="text-sm font-semibold text-slate-900">
                  Cerrar Periodo
                </h3>
                <p className="text-xs text-slate-500">
                  Bloquea nuevos asientos en el mes seleccionado.
                </p>
              </div>
              <div className="ml-auto flex flex-wrap items-end gap-3">
                <div>
                  <label
                    htmlFor="close-month"
                    className="text-xs font-medium text-slate-500"
                  >
                    Mes
                  </label>
                  <input
                    id="close-month"
                    type="number"
                    min={1}
                    max={12}
                    value={closeMonth}
                    onChange={(event) =>
                      setCloseMonth(Number(event.target.value))
                    }
                    className={`${inputStyles} w-24`}
                  />
                </div>
                <div>
                  <label
                    htmlFor="close-year"
                    className="text-xs font-medium text-slate-500"
                  >
                    Año
                  </label>
                  <input
                    id="close-year"
                    type="number"
                    min={2000}
                    max={9999}
                    value={closeYear}
                    onChange={(event) =>
                      setCloseYear(Number(event.target.value))
                    }
                    className={`${inputStyles} w-28`}
                  />
                </div>
                <button
                  type="button"
                  onClick={() => void handleClosePeriod()}
                  disabled={closing}
                  className="inline-flex items-center justify-center rounded-lg bg-violet-600 px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-violet-500 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  {closing ? "Cerrando…" : "Cerrar Periodo"}
                </button>
              </div>
            </div>
            {closeMessage ? (
              <div
                role="status"
                className="mt-3 rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-700"
              >
                {closeMessage}
              </div>
            ) : null}
            {closeError ? (
              <div
                role="alert"
                className="mt-3 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700"
              >
                {closeError}
              </div>
            ) : null}
          </div>
        ) : null}
      </CardContent>
    </Card>
  );
}
