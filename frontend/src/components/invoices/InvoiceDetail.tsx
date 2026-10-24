"use client";

import Link from "next/link";
import { useState } from "react";

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
import { CreditNoteForm } from "@/components/invoices/CreditNoteForm";
import { PaymentForm } from "@/components/invoices/PaymentForm";
import {
  CompanySetting,
  Contact,
  CreditNote,
  Invoice,
  Payment,
} from "@/lib/api";
import {
  formatCurrency,
  formatQuantity,
  formatTaxRate,
} from "@/lib/format";

const lifecycleLabels: Record<Invoice["lifecycle_status"], string> = {
  draft: "Borrador",
  issued: "Emitida",
  void: "Anulada",
};

interface InvoiceDetailProps {
  invoice: Invoice;
  payments: Payment[];
  creditNotes: CreditNote[];
  contact: Contact;
  companySettings: CompanySetting | null;
}

export function InvoiceDetail({
  invoice,
  payments,
  creditNotes,
  contact,
  companySettings,
}: InvoiceDetailProps) {
  const [isPaymentOpen, setIsPaymentOpen] = useState(false);
  const [isCreditNoteOpen, setIsCreditNoteOpen] = useState(false);

  const canRegisterPayment =
    invoice.lifecycle_status === "issued" && Number(invoice.balance) > 0;
  const canCreateCreditNote =
    invoice.lifecycle_status === "issued" && Number(invoice.balance) > 0;

  return (
    <div className="max-w-4xl mx-auto">
      {/* Encabezado de la factura (se imprime) */}
      <div className="mb-8 flex flex-col md:flex-row md:items-baseline justify-between gap-4">
        <div>
          <div className="text-2xl font-bold tracking-tight text-zinc-950">
            {companySettings?.name ?? "FacturaLibre"}
          </div>
          <div className="text-sm text-slate-600">
            {companySettings?.address ? companySettings.address : ""}
            {companySettings?.tax_id ? ` • NIT: ${companySettings.tax_id}` : ""}
            {companySettings?.phone ? ` • Tel: ${companySettings.phone}` : ""}
          </div>
        </div>
        <div className="text-right">
          <div className="text-lg font-bold tabular-nums text-zinc-950">
            {invoice.number ?? "Borrador"}
          </div>
          <span
            className="mt-1 inline-flex items-center rounded-full px-2.5 py-1 text-xs font-semibold ring-1 ring-inset text-slate-600 ring-zinc-200"
          >
            {lifecycleLabels[invoice.lifecycle_status]}
          </span>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4 md:grid-cols-4 mb-8">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wider text-zinc-500">
            Fecha de Emisión
          </p>
          <p className="text-zinc-900">{invoice.issue_date}</p>
        </div>
        <div>
          <p className="text-xs font-semibold uppercase tracking-wider text-zinc-500">
            Fecha de Vencimiento
          </p>
          <p className="text-zinc-900">{invoice.due_date ?? "—"}</p>
        </div>
        <div>
          <p className="text-xs font-semibold uppercase tracking-wider text-zinc-500">
            Cliente
          </p>
          <p className="text-lg font-semibold text-zinc-950">
            {contact.name}
          </p>
        </div>
        <div>
          <p className="text-xs font-semibold uppercase tracking-wider text-zinc-500">
            NIT / Tax ID
          </p>
          <p className="text-zinc-900">{contact.tax_id ?? "—"}</p>
        </div>
      </div>

      {/* Líneas */}
      <Card>
        <CardHeader>
          <CardTitle>Líneas</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <Table>
              <caption className="sr-only">Líneas de la factura</caption>
              <TableHeader>
                <TableRow>
                  <TableHead>Descripción</TableHead>
                  <TableHead className="text-right">Cantidad</TableHead>
                  <TableHead className="text-right">P. Unitario</TableHead>
                  <TableHead className="text-right">Descuento</TableHead>
                  <TableHead className="text-right">Impuesto</TableHead>
                  <TableHead className="text-right">Total Línea</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {invoice.lines.map((line) => (
                  <TableRow key={line.id}>
                    <TableCell className="text-zinc-900">
                      {line.description ?? "Ítem"}
                    </TableCell>
                    <TableCell className="text-right tabular-nums text-zinc-900">
                      {formatQuantity(line.quantity)}
                    </TableCell>
                    <TableCell className="text-right tabular-nums text-zinc-900">
                      {formatCurrency(line.unit_price, invoice.currency)}
                    </TableCell>
                    <TableCell className="text-right tabular-nums text-zinc-900">
                      {Number(line.discount_percent).toFixed(2)} %
                    </TableCell>
                    <TableCell className="text-right tabular-nums text-zinc-900">
                      {formatTaxRate(line.tax_rate)}
                    </TableCell>
                    <TableCell className="text-right tabular-nums font-medium text-zinc-950">
                      {formatCurrency(line.line_total, invoice.currency)}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>

      {/* Totales */}
      <div className="mt-6 flex justify-end">
        <table className="text-right space-y-1">
          <tbody className="divide-y divide-zinc-200">
            <tr className="text-sm text-zinc-600">
              <td className="pr-4">Subtotal</td>
              <td className="tabular-nums">
                {formatCurrency(invoice.subtotal, invoice.currency)}
              </td>
            </tr>
            <tr className="text-sm text-zinc-600">
              <td className="pr-4">Impuestos</td>
              <td className="tabular-nums">
                {formatCurrency(invoice.tax_total, invoice.currency)}
              </td>
            </tr>
            <tr className="font-bold text-zinc-950">
              <td className="pr-4">Total</td>
              <td className="tabular-nums">
                {formatCurrency(invoice.total, invoice.currency)}
              </td>
            </tr>
            <tr className="font-bold text-red-600">
              <td className="pr-4">Balance pendiente</td>
              <td className="tabular-nums">
                {formatCurrency(invoice.balance, invoice.currency)}
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      {/* Pagos */}
      {payments.length > 0 && (
        <Card className="mt-8">
          <CardHeader>
            <CardTitle>Pagos registrados</CardTitle>
            <CardDescription>
              Historial de abonos aplicados a esta factura.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto">
              <Table>
                <caption className="sr-only">Pagos de la factura</caption>
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
                      <TableCell className="text-zinc-900">
                        {payment.payment_date}
                      </TableCell>
                      <TableCell className="text-zinc-900">
                        {payment.method}
                      </TableCell>
                      <TableCell className="text-zinc-900">
                        {payment.reference ?? "—"}
                      </TableCell>
                      <TableCell className="text-right tabular-nums text-zinc-900">
                        {formatCurrency(payment.amount, invoice.currency)}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Notas Crédito */}
      {creditNotes.length > 0 && (
        <Card className="mt-8">
          <CardHeader>
            <CardTitle>Notas crédito</CardTitle>
            <CardDescription>
              Notas crédito asociadas a esta factura.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto">
              <Table>
                <caption className="sr-only">Notas crédito de la factura</caption>
                <TableHeader>
                  <TableRow>
                    <TableHead>Número</TableHead>
                    <TableHead>Fecha</TableHead>
                    <TableHead>Estado</TableHead>
                    <TableHead className="text-right">Total</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {creditNotes.map((cn) => (
                    <TableRow key={cn.id}>
                      <TableCell className="font-mono text-xs text-zinc-950">
                        {cn.number ?? "—"}
                      </TableCell>
                      <TableCell className="text-zinc-900">
                        {cn.issue_date}
                      </TableCell>
                      <TableCell className="text-zinc-900">
                        {cn.status === "issued" ? "Emitida" : "Borrador"}
                      </TableCell>
                      <TableCell className="text-right tabular-nums text-zinc-950">
                        {formatCurrency(cn.total, invoice.currency)}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Acciones (no se imprimen) */}
      <div className="mt-10 flex flex-wrap justify-end gap-2 print:hidden">
        <Link
          href="/invoices"
          className="inline-flex items-center justify-center gap-2 rounded-lg border border-zinc-300 bg-white px-4 py-2 text-sm font-semibold text-zinc-700 shadow-sm transition-colors hover:border-zinc-400 hover:bg-zinc-50 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-zinc-900"
        >
          Volver a Facturas
        </Link>
        <Button onClick={() => window.print()}>
          Imprimir / PDF
        </Button>
        {canRegisterPayment && (
          <Button
            onClick={() => {
              setIsPaymentOpen(true);
            }}
            className="bg-emerald-600 text-white hover:bg-emerald-700"
          >
            Registrar Pago
          </Button>
        )}
        {canCreateCreditNote && (
          <Button
            onClick={() => {
              setIsCreditNoteOpen(true);
            }}
            className="bg-blue-600 text-white hover:bg-blue-700"
          >
            Crear Nota Crédito
          </Button>
        )}
      </div>

      {isPaymentOpen ? (
        <PaymentForm
          invoiceId={invoice.id}
          balance={invoice.balance}
          currency={invoice.currency}
          onClose={() => setIsPaymentOpen(false)}
        />
      ) : null}

      {isCreditNoteOpen ? (
        <CreditNoteForm
          invoice={invoice}
          onClose={() => setIsCreditNoteOpen(false)}
        />
      ) : null}
    </div>
  );
}
