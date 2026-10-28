import type { Metadata } from "next";
import Link from "next/link";
import { ArrowLeft } from "lucide-react";

import { NiifReportsClient } from "@/components/reports/NiifReportsClient";
import {
  getNiifBalanceSheet,
  getNiifCashFlow,
  getNiifIncomeStatement,
  type NiifBalanceSheet,
  type NiifCashFlow,
  type NiifIncomeStatement,
} from "@/lib/api";
import { getSessionCookieHeader } from "@/lib/server-auth";

export const dynamic = "force-dynamic";

export const metadata: Metadata = { title: "Reportes NIIF" };

export default async function NiifReportsPage() {
  const cookieHeader = await getSessionCookieHeader();
  const today = new Date();
  const year = today.getFullYear();
  const fromDate = `${year}-01-01`;
  const toDate = today.toISOString().slice(0, 10);

  let income: NiifIncomeStatement | null = null;
  let balance: NiifBalanceSheet | null = null;
  let cash: NiifCashFlow | null = null;
  let error: string | null = null;

  try {
    [income, balance, cash] = await Promise.all([
      getNiifIncomeStatement(fromDate, toDate, cookieHeader),
      getNiifBalanceSheet(toDate, cookieHeader),
      getNiifCashFlow(fromDate, toDate, cookieHeader),
    ]);
  } catch (cause) {
    error = cause instanceof Error ? cause.message : "No se pudieron consultar los reportes NIIF.";
  }

  return (
    <div className="space-y-6">
      <header>
        <Link
          href="/reports"
          className="inline-flex items-center gap-2 text-sm font-semibold text-amber-700 hover:text-amber-900"
        >
          <ArrowLeft className="size-4" aria-hidden="true" />
          Volver a reportes
        </Link>
        <h1 className="mt-3 text-3xl font-bold tracking-tight text-slate-950">
          Estados financieros NIIF
        </h1>
        <p className="mt-2 max-w-2xl text-slate-600">
          Presentación por función y clasificación corriente / no corriente, con
          flujo de efectivo por método indirecto. Periodo {fromDate} al {toDate}.
        </p>
      </header>
      {error ? (
        <div role="alert" className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      ) : null}
      {income && balance && cash ? (
        <NiifReportsClient income={income} balance={balance} cash={cash} />
      ) : null}
    </div>
  );
}
