import type { Metadata } from "next";

import { BudgetVsActualClient } from "@/components/budgets/BudgetVsActualClient";
import {
  getBudgetVsActualReport,
  getCostCenters,
  type BudgetVsActualReport,
  type CostCenter,
} from "@/lib/api";
import { getSessionCookieHeader } from "@/lib/server-auth";

export const dynamic = "force-dynamic";

export const metadata: Metadata = {
  title: "Presupuesto vs Real",
};

interface BudgetVsActualPageProps {
  searchParams: Promise<{
    period_year?: string;
    period_month?: string;
    cost_center_id?: string;
  }>;
}

export default async function BudgetVsActualPage({
  searchParams,
}: BudgetVsActualPageProps) {
  const cookieHeader = await getSessionCookieHeader();
  const today = new Date();
  const params = await searchParams;

  const periodYear = Number(params.period_year) || today.getFullYear();
  const periodMonth = Number(params.period_month) || today.getMonth() + 1;
  const costCenterId = params.cost_center_id || "";

  let report: BudgetVsActualReport | null = null;
  let costCenters: CostCenter[] = [];
  let error: string | null = null;

  try {
    [report, costCenters] = await Promise.all([
      getBudgetVsActualReport(
        periodYear,
        periodMonth,
        costCenterId || undefined,
        cookieHeader,
      ),
      getCostCenters(false, cookieHeader),
    ]);
  } catch (cause) {
    error =
      cause instanceof Error
        ? cause.message
        : "No se pudo consultar el reporte Presupuesto vs Real.";
  }

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-3xl font-bold tracking-tight text-slate-950">
          Presupuesto vs Real
        </h1>
        <p className="mt-2 max-w-2xl text-slate-600">
          Comparación del gasto presupuestado contra el gasto real de cada
          centro de costo. El real se deriva de los asientos contables
          etiquetados (compras, gastos y nómina del mes).
        </p>
      </header>

      {error ? (
        <div
          role="alert"
          className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700"
        >
          {error}
        </div>
      ) : null}

      <BudgetVsActualClient
        report={report}
        costCenters={costCenters}
        periodYear={periodYear}
        periodMonth={periodMonth}
        costCenterId={costCenterId}
      />
    </div>
  );
}
