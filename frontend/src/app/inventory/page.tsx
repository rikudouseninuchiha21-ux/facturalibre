import type { Metadata } from "next";

import { MovementForm } from "@/components/inventory/MovementForm";
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
import { getStockBalances, type StockBalance } from "@/lib/api";
import { formatQuantity } from "@/lib/format";

export const dynamic = "force-dynamic";

export const metadata: Metadata = {
  title: "Inventario",
};

export default async function InventoryPage() {
  let balances: StockBalance[] = [];
  let error: string | null = null;

  try {
    balances = await getStockBalances();
  } catch (cause) {
    error =
      cause instanceof Error
        ? cause.message
        : "No se pudo consultar el inventario.";
  }

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-3xl font-bold tracking-tight text-slate-950">
          Inventario
        </h1>
        <p className="mt-2 max-w-2xl text-slate-600">
          Saldos actuales por producto y bodega, calculados a partir del libro de
          movimientos.
        </p>
      </header>

      <Card>
        <CardHeader>
          <CardTitle>Registrar Movimiento</CardTitle>
          <CardDescription>
            Registra una entrada o salida de stock. Si no hay existencias
            suficientes, la salida se rechaza y el saldo no cambia.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <MovementForm />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Saldos de Inventario</CardTitle>
          <CardDescription>
            {error
              ? "No fue posible obtener los datos."
              : `${balances.length} saldo${balances.length === 1 ? "" : "s"} de inventario registrado${balances.length === 1 ? "" : "s"}.`}
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
          ) : balances.length === 0 ? (
            <div className="rounded-xl border border-dashed border-slate-300 bg-slate-50 px-6 py-10 text-center">
              <p className="font-medium text-slate-700">
                Todavía no hay saldos de inventario
              </p>
              <p className="mt-1 text-sm text-slate-500">
                Registra una entrada con el formulario de arriba para crear el
                primer saldo.
              </p>
            </div>
          ) : (
            <Table>
              <caption className="sr-only">
                Saldos actuales de inventario
              </caption>
              <TableHeader>
                <TableRow>
                  <TableHead>Producto</TableHead>
                  <TableHead>Bodega</TableHead>
                  <TableHead className="text-right">Cantidad</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {balances.map((balance) => (
                  <TableRow
                    key={`${balance.item_id}-${balance.warehouse_id}`}
                  >
                    <TableCell className="font-medium text-slate-950">
                      {balance.item_name}
                    </TableCell>
                    <TableCell>{balance.warehouse_name}</TableCell>
                    <TableCell className="text-right font-mono font-medium tabular-nums text-slate-950">
                      {formatQuantity(balance.quantity)}
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
