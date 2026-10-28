import type { Metadata } from "next";
import Link from "next/link";
import { ArrowLeft } from "lucide-react";

import { AgingClient } from "@/components/receivables/AgingClient";
import { BucketCards } from "@/components/receivables/BucketCards";
import { getReceivablesAging, type AgingReport } from "@/lib/api";
import { getSessionCookieHeader } from "@/lib/server-auth";

export const dynamic = "force-dynamic";

export const metadata: Metadata = {
  title: "Aging de cartera",
};

interface AgingPageProps {
  searchParams: Promise<{ as_of_date?: string }>;
}

export default async function AgingPage({ searchParams }: AgingPageProps) {
  const cookieHeader = await getSessionCookieHeader();
  const params = await searchParams;
  const asOfDate = params.as_of_date;

  let report: AgingReport | null = null;
  let error: string | null = null;

  try {
    report = await getReceivablesAging(asOfDate, cookieHeader);
  } catch (cause) {
    error =
      cause instanceof Error
        ? cause.message
        : "No se pudo consultar el aging de cartera.";
  }

  return (
    <div className="space-y-6">
      <header>
        <Link
          href="/receivables"
          className="inline-flex items-center gap-2 text-sm font-semibold text-violet-700 transition-colors hover:text-violet-900"
        >
          <ArrowLeft className="size-4" aria-hidden="true" />
          Volver a cartera
        </Link>
        <h1 className="mt-3 text-3xl font-bold tracking-tight text-slate-950">
          Aging de cartera
        </h1>
        <p className="mt-2 max-w-2xl text-slate-600">
          Saldo pendiente por cliente y rango de vencimiento. Exporta el
          reporte filtrado a CSV para Excel.
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

      {report ? (
        <>
          <BucketCards buckets={report.buckets_totals} compact />
          <AgingClient initialReport={report} />
        </>
      ) : null}
    </div>
  );
}
