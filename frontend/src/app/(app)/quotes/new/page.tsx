import type { Metadata } from "next";
import Link from "next/link";

import { QuoteCreateForm } from "@/components/quotes/QuoteCreateForm";
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
  title: "Nueva cotización",
};

function toDateInputValue(date: Date): string {
  return date.toISOString().slice(0, 10);
}

export default async function NewQuotePage() {
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
        : "No se pudieron consultar los datos necesarios para crear la cotización.";
  }

  const today = new Date();
  const expiryDate = new Date(today);
  expiryDate.setUTCDate(expiryDate.getUTCDate() + 30);

  return (
    <div className="space-y-6">
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <Link
            href="/quotes"
            className="text-sm font-medium text-violet-600 transition-colors hover:text-violet-700"
          >
            ← Volver a cotizaciones
          </Link>
          <h1 className="mt-2 text-3xl font-bold tracking-tight text-slate-950">
            Nueva cotización
          </h1>
          <p className="mt-2 max-w-2xl text-slate-600">
            Registra una cotización con sus líneas e impuestos. El número se
            asigna al guardar el borrador.
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
              href="/quotes/new"
              className="inline-flex items-center justify-center rounded-lg bg-violet-600 px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-violet-500"
            >
              Reintentar
            </Link>
          </CardContent>
        </Card>
      ) : (
        <QuoteCreateForm
          contacts={contacts}
          items={items}
          taxes={taxes}
          initialIssueDate={toDateInputValue(today)}
          initialExpiryDate={toDateInputValue(expiryDate)}
        />
      )}
    </div>
  );
}
