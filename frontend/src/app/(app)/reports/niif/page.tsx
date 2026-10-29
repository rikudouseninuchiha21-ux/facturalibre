import type { Metadata } from "next";
import Link from "next/link";
import { ArrowLeft } from "lucide-react";

import { NiifReportsClient } from "@/components/reports/NiifReportsClient";

export const dynamic = "force-dynamic";

export const metadata: Metadata = { title: "Reportes NIIF" };

export default function NiifReportsPage() {
  return (
    <div className="space-y-6">
      <header>
        <Link
          href="/reports"
          className="inline-flex items-center gap-2 text-sm font-semibold text-violet-700 hover:text-violet-900"
        >
          <ArrowLeft className="size-4" aria-hidden="true" />
          Volver a reportes
        </Link>
        <h1 className="mt-3 text-4xl font-bold tracking-tight text-slate-950">
          Cockpit financiero
        </h1>
        <p className="mt-2 max-w-3xl text-slate-600">
          Estados financieros NIIF con comparativos contra el periodo anterior,
          gráficos ejecutivos, auxiliares por cuenta y exportación contable.
        </p>
      </header>
      <NiifReportsClient />
    </div>
  );
}
