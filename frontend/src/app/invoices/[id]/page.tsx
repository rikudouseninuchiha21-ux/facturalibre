import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";

import { InvoiceDetail } from "@/components/invoices/InvoiceDetail";
import {
  ApiError,
  getContact,
  getCreditNotes,
  getInvoice,
  getInvoicePayments,
  type Contact,
  type CreditNote,
  type Invoice,
  type Payment,
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
    title: `Factura ${id}`,
  };
}

export default async function InvoicePage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const cookieHeader = await getSessionCookieHeader();

  let invoice: Invoice | null = null;
  let payments: Payment[] = [];
  let creditNotes: CreditNote[] = [];
  let contact: Contact | null = null;
  let error: string | null = null;

  try {
    // Factura, pagos y notas crédito se consultan en paralelo; el contacto se
    // resuelve tras conocer el contact_id de la factura.
    [invoice, payments, creditNotes] = await Promise.all([
      getInvoice(id, cookieHeader),
      getInvoicePayments(id, cookieHeader),
      getCreditNotes(id, cookieHeader),
    ]);
    contact = await getContact(invoice.contact_id, cookieHeader);
  } catch (cause) {
    if (cause instanceof ApiError && cause.status === 404) {
      notFound();
    }
    error =
      cause instanceof Error
        ? cause.message
        : "No se pudo cargar el detalle de la factura.";
  }

  if (!invoice || !contact) {
    return (
      <div className="max-w-4xl mx-auto py-10">
        <div
          role="alert"
          className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700"
        >
          {error ?? "Factura no encontrada."}
        </div>
        <div className="mt-6 flex justify-end print:hidden">
          <Link
            href="/invoices"
            className="inline-flex items-center justify-center rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 shadow-sm hover:bg-slate-50"
          >
            Volver a Facturas
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <InvoiceDetail
        invoice={invoice}
        payments={payments}
        creditNotes={creditNotes}
        contact={contact}
      />
    </div>
  );
}
