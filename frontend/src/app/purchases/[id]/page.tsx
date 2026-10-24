import Link from "next/link";
import type { Metadata } from "next";
import { notFound } from "next/navigation";

import { PurchaseDetailClient } from "@/components/purchases/PurchaseDetailClient";
import { PurchaseDetailActions } from "@/components/purchases/PurchaseDetailClient";
import {
  ApiError,
  getPurchase,
  getPurchasePayments,
  type Purchase,
  type PurchasePayment,
} from "@/lib/api";
import { getSessionCookieHeader } from "@/lib/server-auth";

export const dynamic = "force-dynamic";

export async function generateMetadata({
  params,
}: {
  params: Promise<{ id: string }>;
}): Promise<Metadata> {
  const { id } = await params;
  return {
    title: `Compra ${id}`,
  };
}

export default async function PurchaseDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const cookieHeader = await getSessionCookieHeader();

  let purchase: Purchase | null = null;
  let payments: PurchasePayment[] = [];
  let error: string | null = null;

  try {
    [purchase, payments] = await Promise.all([
      getPurchase(id, cookieHeader),
      getPurchasePayments(id, cookieHeader),
    ]);
  } catch (cause) {
    if (cause instanceof ApiError && cause.status === 404) {
      notFound();
    }
    error =
      cause instanceof Error
        ? cause.message
        : "No se pudo cargar el detalle de la compra.";
  }

  if (!purchase) {
    return (
      <div className="max-w-4xl mx-auto py-10">
        <div
          role="alert"
          className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700"
        >
          {error ?? "Compra no encontrada."}
        </div>
        <div className="mt-6 flex justify-end print:hidden">
          <Link
            href="/purchases"
            className="inline-flex items-center justify-center rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 shadow-sm hover:bg-slate-50"
          >
            Volver a Compras
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <PurchaseDetailClient purchase={purchase} payments={payments} />
      <PurchaseDetailActions purchase={purchase} />
    </div>
  );
}
