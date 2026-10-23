import type { Metadata } from "next";

import { TaxForm } from "@/components/taxes/TaxForm";
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
import { getTaxes, type Tax } from "@/lib/api";
import { formatTaxRate } from "@/lib/format";
import { getSessionCookieHeader } from "@/lib/server-auth";

export const dynamic = "force-dynamic";

export const metadata: Metadata = {
  title: "Impuestos",
};

function TaxStatus() {
  return (
    <span className="inline-flex items-center rounded-full bg-emerald-50 px-2.5 py-1 text-xs font-semibold text-emerald-700 ring-1 ring-inset ring-emerald-200">
      Activo
    </span>
  );
}

export default async function TaxesPage() {
  const cookieHeader = await getSessionCookieHeader();

  let taxes: Tax[] = [];
  let error: string | null = null;

  try {
    taxes = await getTaxes(cookieHeader);
  } catch (cause) {
    error =
      cause instanceof Error
        ? cause.message
        : "No se pudo consultar el listado de impuestos.";
  }

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-3xl font-bold tracking-tight text-slate-950">
          Impuestos
        </h1>
        <p className="mt-2 max-w-2xl text-slate-600">
          Tasas disponibles para asociar a los ítems y calcular los impuestos de
          cada factura.
        </p>
      </header>

      <Card>
        <CardHeader>
          <CardTitle>Nuevo Impuesto</CardTitle>
          <CardDescription>
            Registra un nombre y una tasa entre 0 y 100. La tasa admite hasta 4
            decimales.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <TaxForm />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Listado</CardTitle>
          <CardDescription>
            {error
              ? "No fue posible obtener los datos."
              : `${taxes.length} impuesto${taxes.length === 1 ? "" : "s"} registrado${taxes.length === 1 ? "" : "s"}.`}
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
          ) : taxes.length === 0 ? (
            <div className="rounded-xl border border-dashed border-slate-300 bg-slate-50 px-6 py-10 text-center">
              <p className="font-medium text-slate-700">
                Todavía no hay impuestos
              </p>
              <p className="mt-1 text-sm text-slate-500">
                Usa el formulario de arriba para crear el primer impuesto.
              </p>
            </div>
          ) : (
            <Table>
              <caption className="sr-only">Listado de impuestos</caption>
              <TableHeader>
                <TableRow>
                  <TableHead>Nombre</TableHead>
                  <TableHead className="text-right">Tasa</TableHead>
                  <TableHead>Estado</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {taxes.map((tax) => (
                  <TableRow key={tax.id}>
                    <TableCell className="font-medium text-slate-950">
                      {tax.name}
                    </TableCell>
                    <TableCell className="text-right font-medium tabular-nums text-slate-950">
                      {formatTaxRate(tax.rate)}
                    </TableCell>
                    <TableCell>
                      <TaxStatus />
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
