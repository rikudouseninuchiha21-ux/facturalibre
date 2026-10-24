import type { Metadata } from "next";
import { notFound } from "next/navigation";

import { QuoteDetail } from "@/components/quotes/QuoteDetail";
import { getQuote, type Quote } from "@/lib/api";
import { getSessionCookieHeader } from "@/lib/server-auth";

export const dynamic = "force-dynamic";

export async function generateMetadata({
  params,
}: { params: Promise<{ id: string }> }): Promise<Metadata> {
  const { id } = await params;
  return { title: `Cotización ${id}` };
}

export default async function QuotePage({
  params,
}: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const cookieHeader = await getSessionCookieHeader();

  let quote: Quote | null = null;
  let error: string | null = null;

  try {
    quote = await getQuote(id, cookieHeader);
  } catch (cause) {
    if (cause instanceof Error && "status" in cause && (cause as { status: number }).status === 404) {
      notFound();
    }
    error =
      cause instanceof Error
        ? cause.message
        : "No se pudo consultar la cotización.";
  }

  if (error || !quote) {
    notFound();
  }

  return (
    <div className="space-y-6">
      <QuoteDetail quote={quote} />
    </div>
  );
}
