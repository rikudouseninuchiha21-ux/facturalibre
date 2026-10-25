import type { Metadata } from "next";

import { CashFlowSection } from "@/components/reports/CashFlowSection";
import { FinancialsClient } from "@/components/reports/FinancialsClient";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  getAgingReport,
  getBalanceSheet,
  getCashFlowReport,
  getCurrentUser,
  getIncomeStatement,
  getLedgerAccounts,
  type AccountingAccount,
} from "@/lib/api";
import { getSessionCookieHeader } from "@/lib/server-auth";

export const dynamic = "force-dynamic";

export const metadata: Metadata = {
  title: "Estados Financieros",
};

export default async function FinancialsPage() {
  const cookieHeader = await getSessionCookieHeader();

  const today = new Date();
  const startOfMonth = new Date(today.getFullYear(), today.getMonth(), 1);
  const endOfMonth = new Date(today.getFullYear(), today.getMonth() + 1, 0);

  const toISODate = (d: Date): string =>
    d.toISOString().slice(0, 10);

  let incomeStatement: Awaited<
    ReturnType<typeof getIncomeStatement>
  > | null = null;
  let balanceSheet: Awaited<ReturnType<typeof getBalanceSheet>> | null = null;
  let aging: Awaited<ReturnType<typeof getAgingReport>> | null = null;
  let cashFlow: Awaited<ReturnType<typeof getCashFlowReport>> | null = null;
  let accounts: AccountingAccount[] = [];
  let isAdmin = false;
  let error: string | null = null;
  let liquidityError: string | null = null;

  try {
    [incomeStatement, balanceSheet] = await Promise.all([
      getIncomeStatement(
        toISODate(startOfMonth),
        toISODate(endOfMonth),
        cookieHeader,
      ),
      getBalanceSheet(toISODate(today), cookieHeader),
    ]);
  } catch (cause) {
    error =
      cause instanceof Error
        ? cause.message
        : "No se pudieron cargar los estados financieros.";
  }

  try {
    const [ledgerAccounts, currentUser] = await Promise.all([
      getLedgerAccounts(undefined, cookieHeader),
      cookieHeader ? getCurrentUser(cookieHeader) : Promise.resolve(null),
    ]);
    accounts = ledgerAccounts;
    isAdmin = currentUser?.role === "ADMIN";
  } catch {
    // El Libro Mayor y el cierre de periodo quedan deshabilitados, pero los
    // reportes existentes pueden seguir mostrándose.
    accounts = [];
    isAdmin = false;
  }

  try {
    [aging, cashFlow] = await Promise.all([
      getAgingReport(cookieHeader),
      getCashFlowReport(cookieHeader),
    ]);
  } catch (cause) {
    liquidityError =
      cause instanceof Error
        ? cause.message
        : "No se pudieron cargar los reportes de cartera y liquidez.";
  }

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-3xl font-bold tracking-tight text-slate-950">
          Estados Financieros
        </h1>
        <p className="mt-2 max-w-2xl text-slate-600">
          Consulta la cartera, la liquidez, el estado de resultados y el balance
          general de la empresa.
        </p>
      </header>

      {liquidityError ? (
        <Card>
          <CardHeader>
            <CardTitle>No se pudo cargar Cartera y Liquidez</CardTitle>
            <CardDescription>
              Revisa la conexión con el backend e inténtalo de nuevo.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div
              role="alert"
              className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700"
            >
              {liquidityError}
            </div>
          </CardContent>
        </Card>
      ) : aging && cashFlow ? (
        <CashFlowSection aging={aging} cashFlow={cashFlow} />
      ) : null}

      {error ? (
        <Card>
          <CardHeader>
            <CardTitle>No se pudo cargar los reportes</CardTitle>
            <CardDescription>
              Revisa la conexión con el backend e inténtalo de nuevo.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div
              role="alert"
              className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700"
            >
              {error}
            </div>
            <button
              onClick={() => window.location.reload()}
              className="inline-flex items-center justify-center rounded-lg bg-slate-900 px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-slate-700"
            >
              Reintentar
            </button>
          </CardContent>
        </Card>
      ) : (
        <FinancialsClient
          incomeStatement={incomeStatement!}
          balanceSheet={balanceSheet!}
          accounts={accounts}
          isAdmin={isAdmin}
          initialStartDate={toISODate(startOfMonth)}
          initialEndDate={toISODate(endOfMonth)}
          initialAsOfDate={toISODate(today)}
        />
      )}
    </div>
  );
}
