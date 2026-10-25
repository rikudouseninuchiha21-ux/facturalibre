import type { Metadata } from "next";

import { BudgetsClient } from "@/components/budgets/BudgetsClient";
import { getBudgets, getCostCenters, type Budget, type CostCenter } from "@/lib/api";
import { getSessionCookieHeader } from "@/lib/server-auth";

export const dynamic = "force-dynamic";

export const metadata: Metadata = {
  title: "Presupuestos",
};

export default async function BudgetsPage() {
  const cookieHeader = await getSessionCookieHeader();

  let budgets: Budget[] = [];
  let costCenters: CostCenter[] = [];
  let error: string | null = null;

  try {
    [budgets, costCenters] = await Promise.all([
      getBudgets(undefined, cookieHeader),
      getCostCenters(false, cookieHeader),
    ]);
  } catch (cause) {
    error =
      cause instanceof Error
        ? cause.message
        : "No se pudo consultar los presupuestos.";
  }

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-3xl font-bold tracking-tight text-slate-950">
          Presupuestos
        </h1>
        <p className="mt-2 max-w-2xl text-slate-600">
          Presupuestos mensuales por centro de costo con líneas por cuenta PUC.
          Solo se pueden editar mientras están en borrador.
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

      <BudgetsClient initialBudgets={budgets} costCenters={costCenters} />
    </div>
  );
}
