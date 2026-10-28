"use client";

import Link from "next/link";
import { useState } from "react";

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
import { PurchasePaymentForm } from "@/components/purchases/PurchasePaymentForm";
import { Purchase, PurchasePayment } from "@/lib/api";
import { formatCurrency } from "@/lib/format";

const purchaseStatusLabels: Record<Purchase["status"], string> = {
  draft: "Borrador",
  issued: "Emitida",
  void: "Anulada",
};

const purchaseStatusStyles: Record<Purchase["status"], string> = {
  draft: "bg-slate-100 text-slate-700 ring-slate-200",
  issued: "bg-emerald-50 text-emerald-700 ring-emerald-200",
  void: "bg-red-50 text-red-700 ring-red-200",
};

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

interface PurchaseDetailClientProps {
  purchase: Purchase;
  payments: PurchasePayment[];
}

export function PurchaseDetailClient({
  purchase,
  payments,
}: PurchaseDetailClientProps) {
  return (
    <div className="max-w-4xl mx-auto">
      <div className="mb-8 flex flex-col md:flex-row md:items-baseline justify-between gap-4">
        <div>
          <div className="text-2xl font-bold tracking-tight text-slate-950">
            VANTAGE
          </div>
          <div className="text-sm text-slate-500">Factura de compra</div>
        </div>
        <div className="text-right">
          <div className="text-lg font-bold tabular-nums text-slate-950">
            {purchase.number ?? "Borrador"}
          </div>
          <span
            className={`mt-1 inline-flex items-center rounded-full px-2.5 py-1 text-xs font-semibold ring-1 ring-inset ${purchaseStatusStyles[purchase.status]}`}
          >
            {purchaseStatusLabels[purchase.status]}
          </span>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4 md:grid-cols-4 mb-8">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">
            Proveedor
          </p>
          <p className="text-slate-900">
            {purchase.supplier?.name ?? "Sin nombre"}
          </p>
        </div>
        <div>
          <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">
            Fecha de Emisión
          </p>
          <p className="text-slate-900">
            {purchase.issue_date ?? "—"}
          </p>
        </div>
        <div>
          <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">
            Fecha de Vencimiento
          </p>
          <p className="text-slate-900">
            {purchase.due_date ?? "—"}
          </p>
        </div>
        <div>
          <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">
            Estado de Pago
          </p>
          <p className="text-slate-900">
            {paymentStatusBadge(purchase.balance, purchase.total)}
          </p>
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Líneas</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <Table>
              <caption className="sr-only">Líneas de la compra</caption>
              <TableHeader>
                <TableRow>
                  <TableHead>Descripción</TableHead>
                  <TableHead className="text-right">Cantidad</TableHead>
                  <TableHead className="text-right">Costo Unitario</TableHead>
                  <TableHead className="text-right">Impuesto</TableHead>
                  <TableHead className="text-right">Total Línea</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {purchase.lines.map((line) => (
                  <TableRow key={line.id}>
                    <TableCell className="text-slate-900">
                      {line.description}
                    </TableCell>
                    <TableCell className="text-right tabular-nums text-slate-900">
                      {line.quantity}
                    </TableCell>
                    <TableCell className="text-right tabular-nums text-slate-900">
                      {formatCurrency(line.unit_cost, "COP")}
                    </TableCell>
                    <TableCell className="text-right tabular-nums text-slate-900">
                      {Number(line.tax_rate).toFixed(2)} %
                    </TableCell>
                    <TableCell className="text-right tabular-nums font-medium text-slate-950">
                      {formatCurrency(line.line_total, "COP")}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>

      <div className="mt-6 flex justify-end">
        <table className="text-right space-y-1">
          <tr className="text-sm text-slate-600">
            <td className="pr-4">Subtotal</td>
            <td className="tabular-nums">
              {formatCurrency(purchase.subtotal, "COP")}
            </td>
          </tr>
          <tr className="text-sm text-slate-600">
            <td className="pr-4">Impuestos</td>
            <td className="tabular-nums">
              {formatCurrency(purchase.tax_total, "COP")}
            </td>
          </tr>
          <tr className="font-bold text-slate-950">
            <td className="pr-4">Total</td>
            <td className="tabular-nums">
              {formatCurrency(purchase.total, "COP")}
            </td>
          </tr>
          <tr className="font-bold text-red-600">
            <td className="pr-4">Balance pendiente</td>
            <td className="tabular-nums">
              {formatCurrency(purchase.balance, "COP")}
            </td>
          </tr>
        </table>
      </div>

      {payments.length > 0 && (
        <Card className="mt-8">
          <CardHeader>
            <CardTitle>Pagos registrados</CardTitle>
            <CardDescription>
              Historial de abonos aplicados a esta factura de compra.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto">
              <Table>
                <caption className="sr-only">Pagos de la compra</caption>
                <TableHeader>
                  <TableRow>
                    <TableHead>Fecha</TableHead>
                    <TableHead>Método</TableHead>
                    <TableHead>Referencia</TableHead>
                    <TableHead className="text-right">Monto</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {payments.map((payment) => (
                    <TableRow key={payment.id}>
                      <TableCell className="text-slate-900">
                        {payment.payment_date}
                      </TableCell>
                      <TableCell className="text-slate-900">
                        {payment.method}
                      </TableCell>
                      <TableCell className="text-slate-900">
                        {payment.reference ?? "—"}
                      </TableCell>
                      <TableCell className="text-right tabular-nums text-slate-900">
                        {formatCurrency(payment.amount, "COP")}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

interface PurchaseDetailActionsProps {
  purchase: Purchase;
}

export function PurchaseDetailActions({
  purchase,
}: PurchaseDetailActionsProps) {
  const [isPaymentOpen, setIsPaymentOpen] = useState(false);

  const canRegisterPayment =
    purchase.status === "issued" && Number(purchase.balance) > 0;

  return (
    <div className="max-w-4xl mx-auto mt-10 flex flex-wrap justify-end gap-2 print:hidden">
      <Link
        href="/purchases"
        className="inline-flex items-center justify-center gap-2 rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 shadow-sm transition-colors hover:border-slate-400 hover:bg-slate-50 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-violet-500"
      >
        Volver a Compras
      </Link>
      <button
        onClick={() => setIsPaymentOpen(true)}
        disabled={!canRegisterPayment}
        className={`inline-flex items-center justify-center rounded-lg bg-emerald-600 px-4 py-2 text-sm font-semibold text-white shadow-sm transition-colors hover:bg-emerald-700 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-600 disabled:opacity-50 disabled:cursor-not-allowed`}
      >
        Registrar Pago
      </button>
      <button
        onClick={() => window.print()}
        className="inline-flex items-center justify-center rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 shadow-sm transition-colors hover:border-slate-400 hover:bg-slate-50 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-violet-500"
      >
        Imprimir / PDF
      </button>
      {isPaymentOpen ? (
        <PurchasePaymentForm
          purchaseId={purchase.id}
          balance={purchase.balance}
          currency="COP"
          onClose={() => setIsPaymentOpen(false)}
        />
      ) : null}
    </div>
  );
}
