import type { Metadata } from "next";

import {
  ApiError,
  getContacts,
  getCrmOpportunities,
  getCrmStages,
  type Contact,
  type CrmOpportunity,
  type CrmStage,
} from "@/lib/api";
import { getSessionCookieHeader } from "@/lib/server-auth";
import { CrmBoard } from "@/components/crm/CrmBoard";

export const dynamic = "force-dynamic";

export const metadata: Metadata = {
  title: "CRM",
};

export default async function CrmPage() {
  const cookieHeader = await getSessionCookieHeader();

  let stages: CrmStage[] = [];
  let opportunities: CrmOpportunity[] = [];
  let contacts: Contact[] = [];
  let error: string | null = null;

  try {
    [stages, opportunities, contacts] = await Promise.all([
      getCrmStages(cookieHeader),
      getCrmOpportunities(cookieHeader),
      getContacts(cookieHeader),
    ]);
  } catch (cause) {
    error =
      cause instanceof ApiError
        ? cause.message
        : "No fue posible cargar el embudo de ventas.";
  }

  return (
    <div className="space-y-6">
      <header className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-sm font-semibold uppercase tracking-wider text-violet-600">
            Operaciones
          </p>
          <h1 className="mt-2 text-3xl font-bold tracking-tight text-slate-950">
            CRM · Embudo de ventas
          </h1>
          <p className="mt-2 max-w-2xl text-slate-600">
            Gestiona tus oportunidades por etapa, registra interacciones y
            conviértelas en cotizaciones sin salir del tablero.
          </p>
        </div>
      </header>

      {error ? (
        <div
          role="alert"
          className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700"
        >
          {error}
        </div>
      ) : (
        <CrmBoard
          initialStages={stages}
          initialOpportunities={opportunities}
          contacts={contacts}
        />
      )}
    </div>
  );
}
