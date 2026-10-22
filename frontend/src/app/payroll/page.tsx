import type { Metadata } from "next";

import { PayrollActions } from "@/components/payroll/PayrollActions";
import { PayrollForm } from "@/components/payroll/PayrollForm";
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
  getPayrollPeriods,
  type PayrollPeriod,
  type PayrollPeriodStatus,
} from "@/lib/api";
import { formatMonth } from "@/lib/format";

export const dynamic = "force-dynamic";

export const metadata: Metadata = {
  title: "Nómina",
};

const statusLabels: Record<PayrollPeriodStatus, string> = {
  DRAFT: "Borrador",
  CLOSED: "Cerrado",
};

const statusStyles: Record<PayrollPeriodStatus, string> = {
  DRAFT: "bg-amber-50 text-amber-700 ring-amber-200",
  CLOSED: "bg-emerald-50 text-emerald-700 ring-emerald-200",
};

function PayrollStatus({ status }: { status: PayrollPeriodStatus }) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-1 text-xs font-semibold ring-1 ring-inset ${statusStyles[status]}`}
    >
      {statusLabels[status]}
    </span>
  );
}

export default async function PayrollPage() {
  let periods: PayrollPeriod[] = [];
  let error: string | null = null;

  try {
    periods = await getPayrollPeriods();
  } catch (cause) {
    error =
      cause instanceof Error
        ? cause.message
        : "No se pudo consultar el listado de periodos de nómina.";
  }

  const now = new Date();

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-3xl font-bold tracking-tight text-slate-950">
          Nómina
        </h1>
        <p className="mt-2 max-w-2xl text-slate-600">
          Periodos mensuales de liquidación, estado del cierre y cálculo de
          deducciones de los empleados activos.
        </p>
      </header>

      <Card>
        <CardHeader>
          <CardTitle>Nuevo Periodo</CardTitle>
          <CardDescription>
            Abre un periodo mensual en borrador. Solo puede existir un periodo
            por mes y año.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <PayrollForm
            defaultMonth={now.getMonth() + 1}
            defaultYear={now.getFullYear()}
          />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Periodos</CardTitle>
          <CardDescription>
            {error
              ? "No fue posible obtener los datos."
              : `${periods.length} periodo${periods.length === 1 ? "" : "s"} de nómina encontrado${periods.length === 1 ? "" : "s"}.`}
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
          ) : periods.length === 0 ? (
            <div className="rounded-xl border border-dashed border-slate-300 bg-slate-50 px-6 py-10 text-center">
              <p className="font-medium text-slate-700">
                Todavía no hay periodos de nómina
              </p>
              <p className="mt-1 text-sm text-slate-500">
                Usa el formulario de arriba para abrir el primer periodo.
              </p>
            </div>
          ) : (
            <Table>
              <caption className="sr-only">Listado de periodos de nómina</caption>
              <TableHeader>
                <TableRow>
                  <TableHead>Mes</TableHead>
                  <TableHead>Año</TableHead>
                  <TableHead>Estado</TableHead>
                  <TableHead className="text-right">Acciones</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {periods.map((period) => (
                  <TableRow key={period.id}>
                    <TableCell className="font-medium text-slate-950">
                      {formatMonth(period.month)}
                    </TableCell>
                    <TableCell className="font-mono text-xs tabular-nums">
                      {period.year}
                    </TableCell>
                    <TableCell>
                      <PayrollStatus status={period.status} />
                    </TableCell>
                    <TableCell className="text-right">
                      <PayrollActions
                        periodId={period.id}
                        status={period.status}
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
