import type { Metadata } from "next";

import { WarehouseForm } from "@/components/warehouses/WarehouseForm";
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
import { getWarehouses, type Warehouse } from "@/lib/api";

export const dynamic = "force-dynamic";

export const metadata: Metadata = {
  title: "Bodegas",
};

function WarehouseStatus({ isActive }: { isActive: boolean }) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-1 text-xs font-semibold ring-1 ring-inset ${
        isActive
          ? "bg-emerald-50 text-emerald-700 ring-emerald-200"
          : "bg-slate-100 text-slate-600 ring-slate-200"
      }`}
    >
      {isActive ? "Activa" : "Inactiva"}
    </span>
  );
}

export default async function WarehousesPage() {
  let warehouses: Warehouse[] = [];
  let error: string | null = null;

  try {
    warehouses = await getWarehouses();
  } catch (cause) {
    error =
      cause instanceof Error
        ? cause.message
        : "No se pudo consultar el listado de bodegas.";
  }

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-3xl font-bold tracking-tight text-slate-950">
          Bodegas
        </h1>
        <p className="mt-2 max-w-2xl text-slate-600">
          Ubicaciones donde FacturaLibre mantiene el stock de los productos.
        </p>
      </header>

      <Card>
        <CardHeader>
          <CardTitle>Nueva Bodega</CardTitle>
          <CardDescription>
            Registra una ubicación con un código único. El nombre y el código
            son obligatorios.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <WarehouseForm />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Listado</CardTitle>
          <CardDescription>
            {error
              ? "No fue posible obtener los datos."
              : `${warehouses.length} bodega${warehouses.length === 1 ? "" : "s"} registrada${warehouses.length === 1 ? "" : "s"}.`}
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
          ) : warehouses.length === 0 ? (
            <div className="rounded-xl border border-dashed border-slate-300 bg-slate-50 px-6 py-10 text-center">
              <p className="font-medium text-slate-700">
                Todavía no hay bodegas
              </p>
              <p className="mt-1 text-sm text-slate-500">
                Usa el formulario de arriba para crear la primera bodega.
              </p>
            </div>
          ) : (
            <Table>
              <caption className="sr-only">Listado de bodegas</caption>
              <TableHeader>
                <TableRow>
                  <TableHead>Código</TableHead>
                  <TableHead>Nombre</TableHead>
                  <TableHead>Estado</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {warehouses.map((warehouse) => (
                  <TableRow key={warehouse.id}>
                    <TableCell className="font-mono text-xs font-medium text-slate-950">
                      {warehouse.code}
                    </TableCell>
                    <TableCell className="font-medium text-slate-950">
                      {warehouse.name}
                    </TableCell>
                    <TableCell>
                      <WarehouseStatus isActive={warehouse.is_active} />
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
