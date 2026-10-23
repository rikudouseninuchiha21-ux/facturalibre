import type { Metadata } from "next";

import { InvoiceActions } from "@/components/invoices/InvoiceActions";
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
import { getInvoices, type Invoice, type LifecycleStatus } from "@/lib/api";
import { getSessionCookieHeader } from "@/lib/server-auth";
import { formatCurrency } from "@/lib/format";

export const dynamic = "force-dynamic";

export const metadata: Metadata = {
  title: "Facturas",
};

const lifecycleLabels: Record<LifecycleStatus, string> = {
  draft: "Borrador",
  issued: "Emitida",
  void: "Anulada",
};

const lifecycleStyles: Record<LifecycleStatus, string> = {
  draft: "bg-slate-100 text-slate-700 ring-slate-200",
  issued: "bg-emerald-50 text-emerald-700 ring-emerald-200",
  void: "bg-red-50 text-red-700 ring-red-200",
};

function LifecycleBadge({ status }: { status: LifecycleStatus }) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-1 text-xs font-semibold ring-1 ring-inset ${lifecycleStyles[status]}`}
    >
      {lifecycleLabels[status]}
    </span>
  );
}

export default async function InvoicesPage() {
  const cookieHeader = await getSessionCookieHeader();

  let invoices: Invoice[] = [];
  let error: string | null = null;

  try {
    invoices = await getInvoices(cookieHeader);
  } catch (cause) {
    error =
      cause instanceof Error
        ? cause.message
        : "No se pudo consultar el listado de facturas.";
  }

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-3xl font-bold tracking-tight text-slate-950">
          Facturas
        </h1>
        <p className="mt-2 max-w-2xl text-slate-600">
          Facturas registradas, con su estado de ciclo de vida y saldo
          pendiente.
        </p>
      </header>

      <Card>
        <CardHeader>
          <CardTitle>Listado</CardTitle>
          <CardDescription>
            {error
              ? "No fue posible obtener los datos."
              : `${invoices.length} factura${invoices.length === 1 ? "" : "s"} encontrada${invoices.length === 1 ? "" : "s"}.`}
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
          ) : invoices.length === 0 ? (
            <div className="rounded-xl border border-dashed border-slate-300 bg-slate-50 px-6 py-10 text-center">
              <p className="font-medium text-slate-700">
                Todavía no hay facturas
              </p>
              <p className="mt-1 text-sm text-slate-500">
                Crea la primera factura a través de la API para verla aquí.
              </p>
            </div>
          ) : (
            <Table>
              <caption className="sr-only">Listado de facturas</caption>
              <TableHeader>
                <TableRow>
                  <TableHead>Número</TableHead>
                  <TableHead>Estado</TableHead>
                  <TableHead className="text-right">Total</TableHead>
                  <TableHead className="text-right">Balance</TableHead>
                  <TableHead className="text-right">Acciones</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {invoices.map((invoice) => (
                  <TableRow key={invoice.id}>
                    <TableCell className="font-mono text-xs font-medium text-slate-950">
                      {invoice.number ?? "—"}
                    </TableCell>
                    <TableCell>
                      <LifecycleBadge status={invoice.lifecycle_status} />
                    </TableCell>
                    <TableCell className="text-right font-medium tabular-nums text-slate-950">
                      {formatCurrency(invoice.total, invoice.currency)}
                    </TableCell>
                    <TableCell className="text-right tabular-nums">
                      {formatCurrency(invoice.balance, invoice.currency)}
                    </TableCell>
                    <TableCell className="text-right">
                      <InvoiceActions
                        invoiceId={invoice.id}
                        status={invoice.lifecycle_status}
                      />
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
