import type { Metadata } from "next";
import Link from "next/link";

import { InvoiceCreateForm } from "@/components/invoices/InvoiceCreateForm";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  getContacts,
  getItems,
  getTaxes,
  type Contact,
  type Item,
  type Tax,
} from "@/lib/api";
import { getSessionCookieHeader } from "@/lib/server-auth";

export const dynamic = "force-dynamic";

export const metadata: Metadata = {
  title: "Nueva factura",
};

function toDateInputValue(date: Date): string {
  return date.toISOString().slice(0, 10);
}

export default async function NewInvoicePage() {
  const cookieHeader = await getSessionCookieHeader();

  let contacts: Contact[] = [];
  let items: Item[] = [];
  let taxes: Tax[] = [];
  let error: string | null = null;

  try {
    [contacts, items, taxes] = await Promise.all([
      getContacts(cookieHeader),
      getItems(cookieHeader),
      getTaxes(cookieHeader),
    ]);
  } catch (cause) {
    error =
      cause instanceof Error
        ? cause.message
        : "No se pudieron consultar los datos necesarios para crear la factura.";
  }

  const today = new Date();
  const dueDate = new Date(today);
  dueDate.setUTCDate(dueDate.getUTCDate() + 30);

  return (
    <div className="space-y-6">
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <Link
            href="/invoices"
            className="text-sm font-medium text-blue-600 transition-colors hover:text-blue-700"
          >
            ← Volver a facturas
          </Link>
          <h1 className="mt-2 text-3xl font-bold tracking-tight text-slate-950">
            Nueva factura
          </h1>
          <p className="mt-2 max-w-2xl text-slate-600">
            Registra un borrador con sus líneas, descuentos e impuestos. El
            número se asigna al emitir la factura.
          </p>
        </div>
      </header>

      {error ? (
        <Card>
          <CardHeader>
            <CardTitle>No se pudo abrir el formulario</CardTitle>
            <CardDescription>
              Revisa la conexión con el backend e inténtalo de nuevo.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div
              role="alert"
              className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700"
            >
              {error}
            </div>
            <Link
              href="/invoices/new"
              className="inline-flex items-center justify-center rounded-lg bg-slate-900 px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-slate-700"
            >
              Reintentar
            </Link>
          </CardContent>
        </Card>
      ) : (
        <InvoiceCreateForm
          contacts={contacts}
          items={items}
          taxes={taxes}
          initialIssueDate={toDateInputValue(today)}
          initialDueDate={toDateInputValue(dueDate)}
        />
      )}
    </div>
  );
}
