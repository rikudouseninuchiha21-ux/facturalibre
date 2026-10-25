import type { Metadata } from "next";
import Link from "next/link";

import { InvoiceActions } from "@/components/invoices/InvoiceActions";
import { ExportCsvButton } from "@/components/reports/ExportCsvButton";
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
  getInvoices,
  type Invoice,
  type LifecycleStatus,
  type PaymentStatus,
} from "@/lib/api";
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

const paymentLabels: Record<PaymentStatus, string> = {
  unpaid: "Pendiente",
  partially_paid: "Parcial",
  paid: "Pagada",
  overpaid: "Sobrepagada",
};

const paymentStyles: Record<PaymentStatus, string> = {
  unpaid: "bg-amber-50 text-amber-700 ring-amber-200",
  partially_paid: "bg-blue-50 text-blue-700 ring-blue-200",
  paid: "bg-emerald-50 text-emerald-700 ring-emerald-200",
  overpaid: "bg-purple-50 text-purple-700 ring-purple-200",
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

function PaymentBadge({ status }: { status: PaymentStatus }) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-1 text-xs font-semibold ring-1 ring-inset ${paymentStyles[status]}`}
    >
      {paymentLabels[status]}
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
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-slate-950">
            Facturas
          </h1>
          <p className="mt-2 max-w-2xl text-slate-600">
            Facturas registradas, con su estado de ciclo de vida, estado de
            pago y saldo pendiente.
          </p>
        </div>
        <Link
          href="/invoices/new"
          className="inline-flex items-center justify-center gap-2 rounded-lg bg-slate-900 px-4 py-2 text-sm font-semibold text-white shadow-sm transition-colors hover:bg-slate-700 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-slate-900"
        >
          <span aria-hidden="true">+</span>
          Nueva Factura
        </Link>
        <ExportCsvButton
          label="Exportar a CSV"
          path="/api/v1/reports/invoices.csv"
          fileName="facturas.csv"
        />
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
                Usa el botón “Nueva Factura” para crear el primer borrador.
              </p>
            </div>
          ) : (
            <Table>
              <caption className="sr-only">Listado de facturas</caption>
              <TableHeader>
                <TableRow>
                  <TableHead>Número</TableHead>
                  <TableHead>Estado</TableHead>
                  <TableHead>Pago</TableHead>
                  <TableHead className="text-right">Total</TableHead>
                  <TableHead className="text-right">Balance</TableHead>
                  <TableHead className="text-right">Acciones</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {invoices.map((invoice) => (
                  <TableRow key={invoice.id}>
                    <TableCell className="font-mono text-xs font-medium text-slate-950">
                      <Link
                        href={`/invoices/${invoice.id}`}
                        className="text-amber-600 hover:underline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-amber-500"
                      >
                        {invoice.number ?? "—"}
                      </Link>
                    </TableCell>
                    <TableCell>
                      <LifecycleBadge status={invoice.lifecycle_status} />
                    </TableCell>
                    <TableCell>
                      <PaymentBadge status={invoice.payment_status} />
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
                        balance={invoice.balance}
                        currency={invoice.currency}
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
