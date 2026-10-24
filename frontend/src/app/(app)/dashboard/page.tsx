import type { Metadata } from "next";
import Link from "next/link";

import { SalesChart } from "@/components/dashboard/SalesChart";
import { StatusChart } from "@/components/dashboard/StatusChart";
import { ExportCsvButton } from "@/components/reports/ExportCsvButton";
import { Wallet, TrendingUp, Clock } from "lucide-react";

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

const sections = [
  {
    href: "/contacts",
    title: "Contactos",
    description:
      "Consulta los clientes y proveedores registrados y crea nuevos contactos.",
  },
  {
    href: "/items",
    title: "Ítems",
    description:
      "Crea productos y servicios con su precio y el impuesto que aplica por defecto.",
  },
  {
    href: "/taxes",
    title: "Impuestos",
    description:
      "Administra las tasas disponibles para calcular los impuestos de las facturas.",
  },
  {
    href: "/invoices",
    title: "Facturas",
    description:
      "Revisa el estado, el saldo pendiente y el estado de pago de cada factura.",
  },
  {
    href: "/warehouses",
    title: "Bodegas",
    description:
      "Crea y consulta las ubicaciones donde se mantiene el stock de los productos.",
  },
  {
    href: "/inventory",
    title: "Inventario",
    description:
      "Consulta los saldos por producto y bodega, y registra entradas o salidas.",
  },
  {
    href: "/employees",
    title: "Empleados",
    description:
      "Registra los empleados activos y consulta su documento y salario base.",
  },
  {
    href: "/payroll",
    title: "Nómina",
    description:
      "Abre periodos mensuales, calcula deducciones y consulta el estado del cierre.",
  },
];

interface KpiCardProps {
  title: string;
  value: string;
  description: string;
  accentClassName: string;
  Icon: React.ElementType;
}

function KpiCard({
  title,
  value,
  description,
  accentClassName,
  Icon: IconComponent,
}: KpiCardProps) {
  return (
    <Card
      className="relative overflow-hidden shadow-sm hover:shadow-md transition-shadow duration-200"
    >
      <span
        aria-hidden="true"
        className={`absolute inset-x-0 top-0 h-1 ${accentClassName}`}
      />
      <CardHeader className="pb-2 flex items-center justify-between">
        <CardDescription>{title}</CardDescription>
        <div className={`flex size-8 items-center justify-center rounded-xl ${accentClassName.replace("bg-", "bg-")} text-white`}>
          <IconComponent className="size-5" />
        </div>
      </CardHeader>
      <p className="text-3xl font-bold tracking-tight tabular-nums text-slate-950">
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
                accentClassName="bg-emerald-500 text-emerald-600"
                Icon={Wallet}
              />
              <KpiCard
                title="Facturado Total"
                value={formatCurrency(summary.total_invoiced)}
                description="Facturas emitidas vigentes."
                accentClassName="bg-indigo-500 text-indigo-600"
                Icon={TrendingUp}
              />
              <KpiCard
                title="Saldo Pendiente"
                value={formatCurrency(summary.pending_balance)}
                description="Cartera por cobrar de facturas emitidas."
                accentClassName="bg-amber-500 text-amber-600"
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

      <section aria-labelledby="accesos-rapidos" className="space-y-4">
        <div>
          <h2
            id="accesos-rapidos"
            className="text-xl font-semibold tracking-tight text-slate-950"
          >
            Accesos rápidos
          </h2>
          <p className="mt-1 text-sm text-slate-600">
            Entra directamente al módulo que necesitas operar.
          </p>
        </div>

        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          {sections.map((section) => (
            <Link
              key={section.href}
              href={section.href}
              className="group block h-full"
            >
              <Card className="h-full transition duration-200 group-hover:-translate-y-0.5 group-hover:border-blue-300 group-hover:shadow-md">
                <CardHeader>
                  <CardTitle>{section.title}</CardTitle>
                  <CardDescription>{section.description}</CardDescription>
                </CardHeader>
                <CardContent>
                  <span className="text-sm font-semibold text-blue-600 group-hover:text-blue-700">
                    Abrir módulo <span aria-hidden="true">→</span>
                  </span>
                </CardContent>
              </Card>
            </Link>
          ))}
        </div>
      </section>
    </div>
  );
}
