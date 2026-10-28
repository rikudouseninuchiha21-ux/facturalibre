import type { Metadata } from "next";
import Link from "next/link";

import { Button } from "@/components/ui/button";
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
import { getPurchases, type Purchase, type PurchaseStatus } from "@/lib/api";
import { getSessionCookieHeader } from "@/lib/server-auth";
import { formatCurrency } from "@/lib/format";

export const dynamic = "force-dynamic";

export const metadata: Metadata = {
  title: "Compras",
};

const purchaseStatusLabels: Record<PurchaseStatus, string> = {
  draft: "Borrador",
  issued: "Emitida",
  void: "Anulada",
};

const purchaseStatusStyles: Record<PurchaseStatus, string> = {
  draft: "bg-slate-100 text-slate-700 ring-slate-200",
  issued: "bg-emerald-50 text-emerald-700 ring-emerald-200",
  void: "bg-red-50 text-red-700 ring-red-200",
};

function StatusBadge({ status }: { status: PurchaseStatus }) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-1 text-xs font-semibold ring-1 ring-inset ${purchaseStatusStyles[status]}`}
    >
      {purchaseStatusLabels[status]}
    </span>
  );
}

function paymentStatusBadge(balance: string, total: string) {
  const bal = Number(balance);
  const tot = Number(total);
  if (bal === 0) {
    return (
      <span className="inline-flex items-center rounded-full px-2.5 py-1 text-xs font-semibold ring-1 ring-inset bg-emerald-50 text-emerald-700 ring-emerald-200">
        Pagada
      </span>
    );
  }
  if (bal < tot) {
    return (
      <span className="inline-flex items-center rounded-full px-2.5 py-1 text-xs font-semibold ring-1 ring-inset bg-blue-50 text-blue-700 ring-blue-200">
        Parcial
      </span>
    );
  }
  return (
    <span className="inline-flex items-center rounded-full px-2.5 py-1 text-xs font-semibold ring-1 ring-inset bg-amber-50 text-amber-700 ring-amber-200">
      Pendiente
    </span>
  );
}

export default async function PurchasesPage() {
  const cookieHeader = await getSessionCookieHeader();

  let purchases: Purchase[] = [];
  let error: string | null = null;

  try {
    purchases = await getPurchases(cookieHeader);
  } catch (cause) {
    error =
      cause instanceof Error
        ? cause.message
        : "No se pudo consultar el listado de compras.";
  }

  return (
    <div className="space-y-6">
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-slate-950">
            Compras
          </h1>
          <p className="mt-2 max-w-2xl text-slate-600">
            Facturas de compra registradas con proveedores, su estado y saldo
            pendiente.
          </p>
        </div>
        <Link
          href="/purchases/new"
          className="inline-flex items-center justify-center gap-2 rounded-lg bg-violet-600 px-4 py-2 text-sm font-semibold text-white shadow-sm transition-colors hover:bg-violet-500 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-violet-500"
        >
          <span aria-hidden="true">+</span>
          Nueva Compra
        </Link>
      </header>

      <Card>
        <CardHeader>
          <CardTitle>Listado</CardTitle>
          <CardDescription>
            {error
              ? "No fue posible obtener los datos."
              : `${purchases.length} compra${purchases.length === 1 ? "" : "s"} encontrada${purchases.length === 1 ? "" : "s"}.`}
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
          ) : purchases.length === 0 ? (
            <div className="rounded-xl border border-dashed border-slate-300 bg-slate-50 px-6 py-10 text-center">
              <p className="font-medium text-slate-700">
                Todavía no hay compras
              </p>
              <p className="mt-1 text-sm text-slate-500">
                Usa el botón “Nueva Compra” para registrar la primera factura
                de proveedor.
              </p>
            </div>
          ) : (
            <Table>
              <caption className="sr-only">Listado de compras</caption>
              <TableHeader>
                <TableRow>
                  <TableHead>Número</TableHead>
                  <TableHead>Proveedor</TableHead>
                  <TableHead>Estado</TableHead>
                  <TableHead className="text-right">Total</TableHead>
                  <TableHead className="text-right">Saldo</TableHead>
                  <TableHead>Pago</TableHead>
                  <TableHead className="text-right">Acciones</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {purchases.map((purchase) => (
                  <TableRow key={purchase.id}>
                    <TableCell className="font-mono text-xs font-medium text-slate-950">
                      <Link
                        href={`/purchases/${purchase.id}`}
                        className="text-violet-600 hover:underline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-violet-500"
                      >
                        {purchase.number ?? "—"}
                      </Link>
                    </TableCell>
                    <TableCell className="text-slate-900">
                      {purchase.supplier?.name ?? "Sin nombre"}
                    </TableCell>
                    <TableCell>
                      <StatusBadge status={purchase.status} />
                    </TableCell>
                    <TableCell className="text-right font-medium tabular-nums text-slate-950">
                      {formatCurrency(purchase.total, "COP")}
                    </TableCell>
                    <TableCell className="text-right tabular-nums">
                      {formatCurrency(purchase.balance, "COP")}
                    </TableCell>
                    <TableCell>
                      {paymentStatusBadge(purchase.balance, purchase.total)}
                    </TableCell>
                    <TableCell className="text-right">
                      {purchase.status === "draft" ? (
                        <Button
                          onClick={() => {
                            // Se emitirá desde el detalle o acción dedicada
                          }}
                          className="border-emerald-200 text-emerald-700 hover:border-emerald-300 hover:bg-emerald-50"
                        >
                          Emitir
                        </Button>
                      ) : null}
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
