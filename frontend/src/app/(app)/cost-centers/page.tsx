import type { Metadata } from "next";

import { CostCentersClient } from "@/components/cost_centers/CostCentersClient";
import { getCostCenters, type CostCenter } from "@/lib/api";
import { getSessionCookieHeader } from "@/lib/server-auth";

export const dynamic = "force-dynamic";

export const metadata: Metadata = {
  title: "Centros de Costo",
};

export default async function CostCentersPage() {
  const cookieHeader = await getSessionCookieHeader();

  let costCenters: CostCenter[] = [];
  let error: string | null = null;

  try {
    costCenters = await getCostCenters(true, cookieHeader);
  } catch (cause) {
    error =
      cause instanceof Error
        ? cause.message
        : "No se pudo consultar los centros de costo.";
  }

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-3xl font-bold tracking-tight text-slate-950">
          Centros de Costo
        </h1>
        <p className="mt-2 max-w-2xl text-slate-600">
          Áreas de la empresa (Ventas, Administración, Producción) usadas para
          atribuir gastos y costos en el reporte Presupuesto vs Real.
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

      <CostCentersClient initialCostCenters={costCenters} />
    </div>
  );
}
