import type { Metadata } from "next";

import { ItemForm } from "@/components/items/ItemForm";
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
import { getItems, getTaxes, type Item, type Tax } from "@/lib/api";
import { formatCurrency } from "@/lib/format";
import { getSessionCookieHeader } from "@/lib/server-auth";

export const dynamic = "force-dynamic";

export const metadata: Metadata = {
  title: "Ítems",
};

export default async function ItemsPage() {
  const cookieHeader = await getSessionCookieHeader();

  let items: Item[] = [];
  let taxes: Tax[] = [];
  let error: string | null = null;

  try {
    [items, taxes] = await Promise.all([
      getItems(cookieHeader),
      getTaxes(cookieHeader),
    ]);
  } catch (cause) {
    error =
      cause instanceof Error
        ? cause.message
        : "No se pudo consultar el listado de ítems.";
  }

  const taxNames = new Map(taxes.map((tax) => [tax.id, tax.name]));

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-3xl font-bold tracking-tight text-slate-950">
          Ítems
        </h1>
        <p className="mt-2 max-w-2xl text-slate-600">
          Productos y servicios disponibles para incluir en las facturas.
        </p>
      </header>

      <Card>
        <CardHeader>
          <CardTitle>Nuevo Ítem</CardTitle>
          <CardDescription>
            Registra el nombre, el precio unitario y, si aplica, el impuesto que
            se usará por defecto en las facturas.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <ItemForm taxes={taxes} />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Listado</CardTitle>
          <CardDescription>
            {error
              ? "No fue posible obtener los datos."
              : `${items.length} ítem${items.length === 1 ? "" : "s"} registrado${items.length === 1 ? "" : "s"}.`}
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
          ) : items.length === 0 ? (
            <div className="rounded-xl border border-dashed border-slate-300 bg-slate-50 px-6 py-10 text-center">
              <p className="font-medium text-slate-700">
                Todavía no hay ítems
              </p>
              <p className="mt-1 text-sm text-slate-500">
                Usa el formulario de arriba para crear el primer ítem.
              </p>
            </div>
          ) : (
            <Table>
              <caption className="sr-only">Listado de ítems</caption>
              <TableHeader>
                <TableRow>
                  <TableHead>Nombre</TableHead>
                  <TableHead>Descripción</TableHead>
                  <TableHead className="text-right">Precio Unitario</TableHead>
                  <TableHead>Impuesto</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {items.map((item) => (
                  <TableRow key={item.id}>
                    <TableCell className="font-medium text-slate-950">
                      {item.name}
                    </TableCell>
                    <TableCell>
                      {item.description ? (
                        <span title={item.description}>
                          {item.description}
                        </span>
                      ) : (
                        "—"
                      )}
                    </TableCell>
                    <TableCell className="text-right font-medium tabular-nums text-slate-950">
                      {formatCurrency(item.unit_price)}
                    </TableCell>
                    <TableCell>
                      {item.tax_id
                        ? (taxNames.get(item.tax_id) ?? "No disponible")
                        : "Ninguno"}
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
