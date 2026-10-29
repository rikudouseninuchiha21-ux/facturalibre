import type { Metadata } from "next";
import Link from "next/link";
import { ArrowRight, BarChart3, FileSpreadsheet } from "lucide-react";

export const dynamic = "force-dynamic";

export const metadata: Metadata = { title: "Reportes" };

const REPORTS = [
  {
    href: "/reports/niif",
    title: "Cockpit financiero NIIF",
    description:
      "Estado de Resultados, Balance General y Flujo de Efectivo con comparativos, drill-down por cuenta, gráficos ejecutivos y exportación.",
    icon: FileSpreadsheet,
  },
  {
    href: "/reports/financials",
    title: "Cartera y liquidez",
    description:
      "Reportes operativos de cartera por cobrar, antigüedad y liquidez del negocio.",
    icon: BarChart3,
  },
];

export default function ReportsPage() {
  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-3xl font-bold tracking-tight text-slate-950">Reportes</h1>
        <p className="mt-2 max-w-2xl text-slate-600">
          Estados financieros y reportes operativos del negocio.
        </p>
      </header>
      <div className="grid gap-4 md:grid-cols-2">
        {REPORTS.map((report) => (
          <Link
            key={report.href}
            href={report.href}
            className="group rounded-2xl border border-zinc-200 bg-white p-5 shadow-sm transition-all hover:border-violet-400 hover:shadow-md"
          >
            <div className="flex items-center gap-4">
              <div className="rounded-xl bg-violet-50 p-3 text-violet-600 group-hover:bg-violet-100">
                <report.icon className="size-6" aria-hidden="true" />
              </div>
              <div className="min-w-0">
                <h2 className="font-semibold text-zinc-900">{report.title}</h2>
                <p className="mt-1 text-sm text-zinc-500">{report.description}</p>
              </div>
              <ArrowRight className="ml-auto size-5 shrink-0 text-violet-600" aria-hidden="true" />
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}
