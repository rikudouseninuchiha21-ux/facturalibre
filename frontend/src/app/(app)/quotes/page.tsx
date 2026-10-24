import type { Metadata } from "next";
import Link from "next/link";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  getQuotes,
  type Quote,
  type QuoteStatus,
} from "@/lib/api";
import { getSessionCookieHeader } from "@/lib/server-auth";
import { formatCurrency } from "@/lib/format";

export const dynamic = "force-dynamic";

export const metadata: Metadata = {
  title: "Cotizaciones",
};

const statusLabels: Record<QuoteStatus, string> = {
  DRAFT: "Borrador",
  SENT: "Enviada",
  ACCEPTED: "Aceptada",
  REJECTED: "Rechazada",
  CONVERTED: "Convertida",
};

const statusStyles: Record<QuoteStatus, string> = {
  DRAFT: "bg-slate-100 text-slate-700 ring-slate-200",
  SENT: "bg-blue-50 text-blue-700 ring-blue-200",
  ACCEPTED: "bg-emerald-50 text-emerald-700 ring-emerald-200",
  REJECTED: "bg-red-50 text-red-700 ring-red-200",
  CONVERTED: "bg-indigo-50 text-indigo-700 ring-indigo-200",
};

function StatusBadge({ status }: { status: QuoteStatus }) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-1 text-xs font-semibold ring-1 ring-inset ${statusStyles[status]}`}
    >
      {statusLabels[status]}
    </span>
  );
}

export default async function QuotesPage() {
  const cookieHeader = await getSessionCookieHeader();

  let quotes: Quote[] = [];
  let error: string | null = null;

  try {
    quotes = await getQuotes(cookieHeader);
  } catch (cause) {
    error =
      cause instanceof Error
        ? cause.message
        : "No se pudo consultar el listado de cotizaciones.";
  }

  return (
    <div className="space-y-6">
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-slate-950">
            Cotizaciones
          </h1>
          <p className="mt-2 max-w-2xl text-slate-600">
            Cotizaciones de venta, con su estado (borrador, enviada, aceptada,
            rechazada o convertida a factura).
          </p>
        </div>
        <Link
          href="/quotes/new"
          className="inline-flex items-center justify-center gap-2 rounded-lg bg-slate-900 px-4 py-2 text-sm font-semibold text-white shadow-sm transition-colors hover:bg-slate-700 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-slate-900"
        >
          <span aria-hidden="true">+</span>
          Nueva Cotización
        </Link>
      </header>

      <Card>
        <CardHeader>
          <CardTitle>Listado</CardTitle>
          <CardDescription>
            {error
              ? "No fue posible obtener los datos."
              : `${quotes.length} cotización${quotes.length === 1 ? "" : "s"} encontrada${quotes.length === 1 ? "" : "s"}.`}
          </CardDescription>
        </CardHeader>
        <CardContent>
          {error ? (
            <div
              role="alert"
              className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700"
            >
              {error}
            </div>
          ) : quotes.length === 0 ? (
            <div className="rounded-xl border border-dashed border-slate-300 bg-slate-50 px-6 py-10 text-center">
              <p className="font-medium text-slate-700">
                Todavía no hay cotizaciones
              </p>
              <p className="mt-1 text-sm text-slate-500">
                Usa el botón “Nueva Cotización” para crear el primer borrador.
              </p>
            </div>
          ) : (
            <Table>
              <caption className="sr-only">Listado de cotizaciones</caption>
              <TableHeader>
                <TableRow>
                  <TableHead>Número</TableHead>
                  <TableHead>Contacto</TableHead>
                  <TableHead>Estado</TableHead>
                  <TableHead className="text-right">Total</TableHead>
                  <TableHead className="text-right">Vence</TableHead>
                  <TableHead className="text-right">Acciones</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {quotes.map((quote) => (
                  <TableRow key={quote.id}>
                    <TableCell className="font-mono text-xs font-medium text-slate-950">
                      <Link
                        href={`/quotes/${quote.id}`}
                        className="text-blue-600 hover:underline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-500"
                      >
                        {quote.number ?? "—"}
                      </Link>
                    </TableCell>
                    <TableCell className="text-slate-900">{quote.contact_name}</TableCell>
                    <TableCell>
                      <StatusBadge status={quote.status} />
                    </TableCell>
                    <TableCell className="text-right font-medium tabular-nums text-slate-950">
                      {formatCurrency(quote.total, quote.currency)}
                    </TableCell>
                    <TableCell className="text-right text-slate-600">
                      {quote.expiry_date ?? "—"}
                    </TableCell>
                    <TableCell className="text-right">
                      <Link
                        href={`/quotes/${quote.id}`}
                        className="text-sm font-medium text-blue-600 hover:underline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-500"
                      >
                        Ver detalle
                      </Link>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
