"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  ApiError,
  convertQuoteToInvoice,
  type Quote,
} from "@/lib/api";
import { formatCurrency } from "@/lib/format";

const statusLabels: Record<string, string> = {
  DRAFT: "Borrador",
  SENT: "Enviada",
  ACCEPTED: "Aceptada",
  REJECTED: "Rechazada",
  CONVERTED: "Convertida",
};

const statusStyles: Record<string, string> = {
  DRAFT: "bg-slate-100 text-slate-700 ring-slate-200",
  SENT: "bg-blue-50 text-blue-700 ring-blue-200",
  ACCEPTED: "bg-emerald-50 text-emerald-700 ring-emerald-200",
  REJECTED: "bg-red-50 text-red-700 ring-red-200",
  CONVERTED: "bg-indigo-50 text-indigo-700 ring-indigo-200",
};

interface QuoteDetailProps {
  quote: Quote;
}

export function QuoteDetail({ quote }: QuoteDetailProps) {
  const router = useRouter();
  const [isConverting, setIsConverting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const canConvert = quote.status === "ACCEPTED" && !quote.converted_invoice_id;

  async function handleConvert() {
    setError(null);
    setIsConverting(true);
    try {
      await convertQuoteToInvoice(quote.id);
      router.refresh();
    } catch (cause) {
      setError(
        cause instanceof ApiError
          ? `No se pudo convertir la cotización: ${cause.message}`
          : "No se pudo convertir la cotización. Revisa tu conexión e inténtalo de nuevo.",
      );
    } finally {
      setIsConverting(false);
    }
  }

  return (
    <div className="space-y-6">
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-slate-950">
            Cotización
          </h1>
          <p className="mt-2 max-w-2xl text-slate-600">
            Detalle de la cotización {quote.number ?? "sin número"} y sus
            líneas.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Link
            href="/quotes"
            className="inline-flex items-center justify-center gap-2 rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 shadow-sm transition-colors hover:border-slate-400 hover:bg-slate-50 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-slate-900"
          >
            ← Volver a cotizaciones
          </Link>
          {canConvert && (
            <Button
              onClick={handleConvert}
              disabled={isConverting}
              className="bg-emerald-600 hover:bg-emerald-700 shadow-sm shadow-emerald-500/30"
            >
              {isConverting ? "Convirtiendo..." : "Convertir a Factura"}
            </Button>
          )}
          {quote.converted_invoice_id && (
            <span className="inline-flex items-center rounded-full px-2.5 py-1 text-xs font-semibold bg-emerald-50 text-emerald-700 ring-1 ring-inset ring-emerald-200">
              Convertida a factura
            </span>
          )}
        </div>
      </header>

      {error ? (
        <div
          role="alert"
          className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700"
        >
          {error}
        </div>
      ) : null}

      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader>
            <CardTitle>Datos generales</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex items-start justify-between gap-2">
              <span className="text-sm text-slate-500">Número</span>
              <span className="text-sm font-medium text-slate-950">
                {quote.number ?? "—"}
              </span>
            </div>
            <div className="flex items-start justify-between gap-2">
              <span className="text-sm text-slate-500">Contacto</span>
              <span className="text-sm font-medium text-slate-950">
                {quote.contact_id}
              </span>
            </div>
            <div className="flex items-start justify-between gap-2">
              <span className="text-sm text-slate-500">Estado</span>
              <span
                className={`inline-flex items-center rounded-full px-2.5 py-1 text-xs font-semibold ring-1 ring-inset ${statusStyles[quote.status]}`}
              >
                {statusLabels[quote.status]}
              </span>
            </div>
            <div className="flex items-start justify-between gap-2">
              <span className="text-sm text-slate-500">Fecha de emisión</span>
              <span className="text-sm font-medium text-slate-950">
                {quote.issue_date}
              </span>
            </div>
            <div className="flex items-start justify-between gap-2">
              <span className="text-sm text-slate-500">Fecha de vencimiento</span>
              <span className="text-sm font-medium text-slate-950">
                {quote.expiry_date ?? "—"}
              </span>
            </div>
            <div className="flex items-start justify-between gap-2">
              <span className="text-sm text-slate-500">Moneda</span>
              <span className="text-sm font-medium text-slate-950">
                {quote.currency}
              </span>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Totales</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex items-start justify-between gap-2">
              <span className="text-sm text-slate-500">Subtotal</span>
              <span className="text-sm font-medium tabular-nums text-slate-950">
                {formatCurrency(quote.subtotal, quote.currency)}
              </span>
            </div>
            <div className="flex items-start justify-between gap-2">
              <span className="text-sm text-slate-500">Impuesto</span>
              <span className="text-sm font-medium tabular-nums text-slate-950">
                {formatCurrency(quote.tax_total, quote.currency)}
              </span>
            </div>
            <div className="flex items-start justify-between gap-2 border-t border-slate-200 pt-2">
              <span className="text-sm font-semibold text-slate-900">Total</span>
              <span className="text-sm font-bold tabular-nums text-slate-950">
                {formatCurrency(quote.total, quote.currency)}
              </span>
            </div>
          </CardContent>
        </Card>

        {quote.converted_invoice_id && (
          <Card>
            <CardHeader>
              <CardTitle>Convertida a factura</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="flex items-start justify-between gap-2">
                <span className="text-sm text-slate-500">Factura</span>
                <span className="text-sm font-medium tabular-nums text-slate-950">
                  {quote.converted_invoice_id}
                </span>
              </div>
            </CardContent>
          </Card>
        )}
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Líneas</CardTitle>
          <CardDescription>
            {quote.lines.length} línea{quote.lines.length === 1 ? "" : "s"} en
            esta cotización.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-slate-200">
                  <th className="text-xs font-semibold text-slate-500 py-3 px-4">
                    Ítem
                  </th>
                  <th className="text-xs font-semibold text-slate-500 py-3 px-4 text-right">
                    Cantidad
                  </th>
                  <th className="text-xs font-semibold text-slate-500 py-3 px-4 text-right">
                    Precio Unit.
                  </th>
                  <th className="text-xs font-semibold text-slate-500 py-3 px-4 text-right">
                    Impuesto %
                  </th>
                  <th className="text-xs font-semibold text-slate-500 py-3 px-4 text-right">
                    Subtotal
                  </th>
                  <th className="text-xs font-semibold text-slate-500 py-3 px-4 text-right">
                    Total
                  </th>
                </tr>
              </thead>
              <tbody>
                {quote.lines.map((line) => (
                  <tr key={line.id} className="border-b border-slate-100">
                    <td className="py-3 px-4 text-sm text-slate-900">
                      {line.description}
                    </td>
                    <td className="py-3 px-4 text-sm tabular-nums text-slate-900 text-right">
                      {line.quantity}
                    </td>
                    <td className="py-3 px-4 text-sm tabular-nums text-slate-900 text-right">
                      {formatCurrency(line.unit_price, quote.currency)}
                    </td>
                    <td className="py-3 px-4 text-sm tabular-nums text-slate-900 text-right">
                      {line.tax_rate}%
                    </td>
                    <td className="py-3 px-4 text-sm tabular-nums text-slate-900 text-right">
                      {formatCurrency(line.line_subtotal, quote.currency)}
                    </td>
                    <td className="py-3 px-4 text-sm font-medium tabular-nums text-slate-950 text-right">
                      {formatCurrency(line.line_total, quote.currency)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
