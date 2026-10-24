import type { Metadata } from "next";
import Link from "next/link";

import { SalesChart } from "@/components/dashboard/SalesChart";
import { StatusChart } from "@/components/dashboard/StatusChart";
import { ExportCsvButton } from "@/components/reports/ExportCsvButton";
import { Wallet, TrendingUp, Clock, ShoppingCart, FilePlus, UserPlus, BarChart3 } from "lucide-react";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { getDashboardSummary, type DashboardSummary } from "@/lib/api";
import { formatCurrency } from "@/lib/format";
import { getSessionCookieHeader } from "@/lib/server-auth";

export const dynamic = "force-dynamic";

export const metadata: Metadata = {
  title: "Panel de control",
};

interface KpiCardProps {
  title: string;
  value: string;
  description: string;
  cardClassName: string;
  iconClassName: string;
  textClassName: string;
  Icon: React.ElementType;
}

function KpiCard({
  title,
  value,
  description,
  cardClassName,
  iconClassName,
  textClassName,
  Icon: IconComponent,
}: KpiCardProps) {
  return (
    <Card className={`relative overflow-hidden ${cardClassName}`}>
      <span
        aria-hidden="true"
        className="absolute inset-x-0 top-0 h-1 bg-white/40"
      />
      <CardHeader className="pb-2 flex items-center justify-between">
        <CardDescription>{title}</CardDescription>
        <div className={`flex size-10 items-center justify-center rounded-xl ${iconClassName}`}>
          <IconComponent className="size-5" />
        </div>
      </CardHeader>
      <p className={`text-3xl font-bold tracking-tight tabular-nums ${textClassName}`}>
        {value}
      </p>
      <CardContent>
        <p className="text-sm text-slate-500">{description}</p>
      </CardContent>
    </Card>
  );
}

export default async function HomePage() {
  const cookieHeader = await getSessionCookieHeader();

  let summary: DashboardSummary | null = null;
  let error: string | null = null;

  try {
    summary = await getDashboardSummary(cookieHeader);
  } catch (cause) {
    error =
      cause instanceof Error
        ? cause.message
        : "No se pudo consultar el resumen del negocio.";
  }

  return (
    <div className="space-y-8">
      <header className="max-w-3xl">
        <p className="text-sm font-semibold uppercase tracking-widest text-blue-600">
          Panel administrativo
        </p>
        <h1 className="mt-2 text-3xl font-bold tracking-tight text-slate-950 sm:text-4xl">
          Resumen del negocio
        </h1>
        <p className="mt-3 text-base leading-7 text-slate-600">
          Ingresos recibidos, facturación emitida y cartera pendiente en una
          vista consolidada.
        </p>
        <ExportCsvButton
          label="Exportar pagos a CSV"
          path="/api/v1/reports/payments.csv"
          fileName="pagos.csv"
        />
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
          <section aria-labelledby="indicadores-title" className="space-y-4">
            <h2 id="indicadores-title" className="sr-only">
              Indicadores financieros
            </h2>
            <div className="grid gap-4 md:grid-cols-3">
              <KpiCard
                title="Ingresos Totales"
                value={formatCurrency(summary.total_revenue)}
                description="Pagos recibidos sobre facturas."
                cardClassName="bg-gradient-to-br from-emerald-50 to-white border-emerald-100 shadow-sm hover:shadow-md hover:border-emerald-200 transition-all"
                iconClassName="bg-gradient-to-br from-emerald-400 to-emerald-600 text-white shadow-lg shadow-emerald-500/30"
                textClassName="text-emerald-950"
                Icon={Wallet}
              />
              <KpiCard
                title="Facturado Total"
                value={formatCurrency(summary.total_invoiced)}
                description="Facturas emitidas vigentes."
                cardClassName="bg-gradient-to-br from-indigo-50 to-white border-indigo-100 shadow-sm hover:shadow-md hover:border-indigo-200 transition-all"
                iconClassName="bg-gradient-to-br from-indigo-400 to-indigo-600 text-white shadow-lg shadow-indigo-500/30"
                textClassName="text-indigo-950"
                Icon={TrendingUp}
              />
              <KpiCard
                title="Saldo Pendiente"
                value={formatCurrency(summary.pending_balance)}
                description="Cartera por cobrar de facturas emitidas."
                cardClassName="bg-gradient-to-br from-amber-50 to-white border-amber-100 shadow-sm hover:shadow-md hover:border-amber-200 transition-all"
                iconClassName="bg-gradient-to-br from-amber-400 to-amber-600 text-white shadow-lg shadow-amber-500/30"
                textClassName="text-amber-950"
                Icon={Clock}
              />
            </div>
          </section>

          <div className="grid gap-6 xl:grid-cols-5">
            <Card className="xl:col-span-3">
              <CardHeader>
                <CardTitle>Ventas mensuales</CardTitle>
                <CardDescription>
                  Facturación emitida en los últimos seis meses.
                </CardDescription>
              </CardHeader>
              <CardContent>
                <SalesChart data={summary.monthly_sales} />
              </CardContent>
            </Card>

            <Card className="xl:col-span-2">
              <CardHeader>
                <CardTitle>Facturas por estado</CardTitle>
                <CardDescription>
                  Distribución del ciclo de vida de las facturas registradas.
                </CardDescription>
              </CardHeader>
              <CardContent>
                <StatusChart data={summary.invoices_by_status} />
              </CardContent>
            </Card>
          </div>
        </>
      ) : null}

      <section className="mt-8">
        <h2 className="text-xl font-bold tracking-tight text-zinc-950 mb-4">
          Accesos Rápidos
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <Link
            href="/pos"
            className="group rounded-2xl border border-zinc-200 bg-white p-5 shadow-sm hover:border-indigo-300 hover:shadow-md transition-all"
          >
            <div className="flex items-center gap-4">
              <div className="p-3 rounded-xl bg-indigo-50 text-indigo-600 group-hover:bg-indigo-100 transition-colors">
                <ShoppingCart className="size-6" />
              </div>
              <div>
                <h3 className="font-semibold text-zinc-900">Punto de Venta</h3>
                <p className="text-sm text-zinc-500">Vender rápido</p>
              </div>
            </div>
          </Link>
          <Link
            href="/invoices/new"
            className="group rounded-2xl border border-zinc-200 bg-white p-5 shadow-sm hover:border-emerald-300 hover:shadow-md transition-all"
          >
            <div className="flex items-center gap-4">
              <div className="p-3 rounded-xl bg-emerald-50 text-emerald-600 group-hover:bg-emerald-100 transition-colors">
                <FilePlus className="size-6" />
              </div>
              <div>
                <h3 className="font-semibold text-zinc-900">Nueva Factura</h3>
                <p className="text-sm text-zinc-500">Facturar cliente</p>
              </div>
            </div>
          </Link>
          <Link
            href="/contacts"
            className="group rounded-2xl border border-zinc-200 bg-white p-5 shadow-sm hover:border-amber-300 hover:shadow-md transition-all"
          >
            <div className="flex items-center gap-4">
              <div className="p-3 rounded-xl bg-amber-50 text-amber-600 group-hover:bg-amber-100 transition-colors">
                <UserPlus className="size-6" />
              </div>
              <div>
                <h3 className="font-semibold text-zinc-900">Nuevo Contacto</h3>
                <p className="text-sm text-zinc-500">Agregar cliente</p>
              </div>
            </div>
          </Link>
          <Link
            href="/reports/financials"
            className="group rounded-2xl border border-zinc-200 bg-white p-5 shadow-sm hover:border-rose-300 hover:shadow-md transition-all"
          >
            <div className="flex items-center gap-4">
              <div className="p-3 rounded-xl bg-rose-50 text-rose-600 group-hover:bg-rose-100 transition-colors">
                <BarChart3 className="size-6" />
              </div>
              <div>
                <h3 className="font-semibold text-zinc-900">Ver Reportes</h3>
                <p className="text-sm text-zinc-500">Estados financieros</p>
              </div>
            </div>
          </Link>
        </div>
      </section>
    </div>
  );
}
