import type { Metadata } from "next";
import Link from "next/link";
import {
  AlertCircle,
  ArrowRight,
  Clock,
  Receipt,
  Users,
  Wallet,
} from "lucide-react";

import { BucketCards } from "@/components/receivables/BucketCards";
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
import { getReceivablesSummary, type ReceivablesSummary } from "@/lib/api";
import { formatCurrency } from "@/lib/format";
import { getSessionCookieHeader } from "@/lib/server-auth";

export const dynamic = "force-dynamic";

export const metadata: Metadata = {
  title: "Cartera",
};

export default async function ReceivablesPage() {
  const cookieHeader = await getSessionCookieHeader();

  let summary: ReceivablesSummary | null = null;
  let error: string | null = null;

  try {
    summary = await getReceivablesSummary(undefined, cookieHeader);
  } catch (cause) {
    error =
      cause instanceof Error
        ? cause.message
        : "No se pudo consultar la cartera.";
  }

  return (
    <div className="space-y-8">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div className="max-w-2xl">
          <p className="text-sm font-semibold uppercase tracking-widest text-violet-600">
            Cobranza
          </p>
          <h1 className="mt-2 text-3xl font-bold tracking-tight text-slate-950 sm:text-4xl">
            Cartera por cobrar
          </h1>
          <p className="mt-3 text-base leading-7 text-slate-600">
            Aging por cliente, saldos vencidos y prioridades de cobranza
            calculados al día de hoy.
          </p>
        </div>
        <div className="flex flex-wrap gap-3">
          <Link
            href="/receivables/aging"
            className="inline-flex items-center gap-2 rounded-lg bg-violet-600 px-4 py-2 text-sm font-semibold text-white shadow-sm transition-colors hover:bg-violet-500"
          >
            Ver aging completo
            <ArrowRight className="size-4" aria-hidden="true" />
          </Link>
        </div>
      </header>

      {error ? (
        <div
          role="alert"
          className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700"
        >
          {error}
        </div>
      ) : null}

      {summary ? (
        <>
          <section className="grid gap-4 md:grid-cols-3">
            <Card className="bg-gradient-to-br from-violet-100 to-white">
              <CardHeader className="pb-2 flex flex-row items-center justify-between">
                <CardDescription>Total por cobrar</CardDescription>
                <span className="flex size-9 items-center justify-center rounded-xl bg-violet-600 text-white">
                  <Wallet className="size-4" aria-hidden="true" />
                </span>
              </CardHeader>
              <CardContent>
                <p className="text-3xl font-bold tracking-tight text-violet-950 tabular-nums">
                  {formatCurrency(summary.buckets_totals.total)}
                </p>
                <p className="mt-1 text-sm text-zinc-500">
                  {summary.customer_count} cliente
                  {summary.customer_count === 1 ? "" : "s"} con saldo.
                </p>
              </CardContent>
            </Card>

            <Card className="bg-gradient-to-br from-red-50 to-white">
              <CardHeader className="pb-2 flex flex-row items-center justify-between">
                <CardDescription>Total vencido</CardDescription>
                <span className="flex size-9 items-center justify-center rounded-xl bg-red-600 text-white">
                  <AlertCircle className="size-4" aria-hidden="true" />
                </span>
              </CardHeader>
              <CardContent>
                <p className="text-3xl font-bold tracking-tight text-red-950 tabular-nums">
                  {formatCurrency(summary.total_overdue)}
                </p>
                <p className="mt-1 text-sm text-zinc-500">
                  Facturas con vencimiento superado.
                </p>
              </CardContent>
            </Card>

            <Card className="bg-gradient-to-br from-emerald-50 to-white">
              <CardHeader className="pb-2 flex flex-row items-center justify-between">
                <CardDescription>Cartera corriente</CardDescription>
                <span className="flex size-9 items-center justify-center rounded-xl bg-emerald-600 text-white">
                  <Clock className="size-4" aria-hidden="true" />
                </span>
              </CardHeader>
              <CardContent>
                <p className="text-3xl font-bold tracking-tight text-emerald-950 tabular-nums">
                  {formatCurrency(summary.buckets_totals.current)}
                </p>
                <p className="mt-1 text-sm text-zinc-500">
                  Aún dentro del plazo pactado.
                </p>
              </CardContent>
            </Card>
          </section>

          <section aria-labelledby="buckets-title" className="space-y-3">
            <h2
              id="buckets-title"
              className="text-lg font-semibold tracking-tight text-zinc-950"
            >
              Distribución por vencimiento
            </h2>
            <BucketCards buckets={summary.buckets_totals} />
          </section>

          <Card>
            <CardHeader>
              <CardTitle>Top clientes por deuda</CardTitle>
              <CardDescription>
                Los diez clientes con mayor saldo pendiente. Haz clic para ver
                su estado de cuenta.
              </CardDescription>
            </CardHeader>
            <CardContent>
              {summary.top_customers.length === 0 ? (
                <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-emerald-200 bg-emerald-50/60 px-6 py-10 text-center">
                  <Receipt
                    className="size-10 text-emerald-500"
                    aria-hidden="true"
                  />
                  <p className="mt-3 font-semibold text-emerald-900">
                    Sin cartera pendiente
                  </p>
                  <p className="mt-1 text-sm text-emerald-700">
                    Todas las facturas emitidas están pagadas.
                  </p>
                </div>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Cliente</TableHead>
                      <TableHead className="text-right">Corriente</TableHead>
                      <TableHead className="text-right">Vencido</TableHead>
                      <TableHead className="text-right">Total</TableHead>
                      <TableHead className="text-right">Facturas</TableHead>
                      <TableHead className="text-right">Detalle</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {summary.top_customers.map((customer) => (
                      <TableRow key={customer.contact_id}>
                        <TableCell className="font-medium text-zinc-900">
                          {customer.contact_name}
                        </TableCell>
                        <TableCell className="text-right tabular-nums text-zinc-600">
                          {formatCurrency(customer.current)}
                        </TableCell>
                        <TableCell className="text-right font-medium tabular-nums text-red-700">
                          {formatCurrency(customer.total_overdue)}
                        </TableCell>
                        <TableCell className="text-right font-semibold tabular-nums text-zinc-950">
                          {formatCurrency(customer.total)}
                        </TableCell>
                        <TableCell className="text-right tabular-nums text-zinc-600">
                          {customer.invoice_count}
                        </TableCell>
                        <TableCell className="text-right">
                          <Link
                            href={`/receivables/customers/${customer.contact_id}`}
                            className="inline-flex items-center gap-1 text-sm font-semibold text-violet-700 hover:text-violet-900"
                          >
                            Ver
                            <ArrowRight className="size-3.5" aria-hidden="true" />
                          </Link>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>

          <div className="flex items-center gap-2 rounded-xl border border-zinc-200 bg-white px-4 py-3 text-sm text-zinc-600">
            <Users className="size-4 text-violet-600" aria-hidden="true" />
            El aging se calcula con los pagos y notas crédito reales. Los
            acuerdos de pago son de gestión y no alteran la contabilidad.
          </div>
        </>
      ) : null}
    </div>
  );
}
