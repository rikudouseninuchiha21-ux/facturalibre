"use client";

import Link from "next/link";
import { useState } from "react";
import { FileCode, FileText, RefreshCw } from "lucide-react";

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
import { InvoiceDianBadge } from "@/components/invoices/InvoiceDianBadge";
import { PaymentForm } from "@/components/invoices/PaymentForm";
import {
  ApiError,
  CompanySetting,
  Contact,
  CreditNote,
  Invoice,
  Payment,
  downloadInvoicePdf,
  downloadInvoiceXml,
  regenerateInvoiceCufe,
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

const paymentMeanLabels: Record<string, string> = {
  "10": "Efectivo",
  "20": "Cheque",
  "42": "Transferencia",
  "48": "Tarjeta crédito",
  "49": "Tarjeta débito",
  ZZZ: "Otros",
};

interface InvoiceDetailProps {
  invoice: Invoice;
  payments: Payment[];
  creditNotes: CreditNote[];
  contact: Contact;
  companySettings: CompanySetting | null;
  canRegenerateCufe?: boolean;
}

export function InvoiceDetail({
  invoice,
  payments,
  creditNotes,
  contact,
  companySettings,
  canRegenerateCufe = false,
}: InvoiceDetailProps) {
  const [isPaymentOpen, setIsPaymentOpen] = useState(false);
  const [isCreditNoteOpen, setIsCreditNoteOpen] = useState(false);
  const [dianBusy, setDianBusy] = useState<"xml" | "pdf" | "cufe" | null>(
    null,
  );
  const [dianError, setDianError] = useState<string | null>(null);
  const [dianSuccess, setDianSuccess] = useState<string | null>(null);

  const isIssued = invoice.lifecycle_status === "issued";
  const canRegisterPayment =
    invoice.lifecycle_status === "issued" && Number(invoice.balance) > 0;
  const canCreateCreditNote =
    invoice.lifecycle_status === "issued" && Number(invoice.balance) > 0;
  const hasPendingBalance = Number(invoice.balance) > 0;

  return (
    <div className="max-w-4xl mx-auto">
      <div className="bg-white print:w-full print:max-w-[210mm] print:mx-auto print:shadow-none p-8 rounded-xl shadow-sm border border-zinc-200">
        {/* Encabezado de la factura (se imprime) */}
        <div className="mb-8 flex flex-col gap-4 md:flex-row md:items-start md:justify-between print:flex-row print:items-start print:justify-between">
          <div className="min-w-0">
            <div className="text-2xl font-bold tracking-tight text-zinc-950">
              {companySettings?.name ?? "VANTAGE"}
            </div>
            <div className="mt-1 space-y-0.5 text-sm text-slate-600">
              {companySettings?.address ? (
                <div>{companySettings.address}</div>
              ) : null}
              {companySettings?.tax_id ? (
                <div>NIT: {companySettings.tax_id}</div>
              ) : null}
              {companySettings?.phone ? (
                <div>Tel: {companySettings.phone}</div>
              ) : null}
            </div>
          </div>
          <div className="shrink-0 text-right">
            <div className="text-xs font-semibold uppercase tracking-wider text-zinc-500">
              Factura de venta
            </div>
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
          <div>
            <p className="text-xs font-semibold uppercase tracking-wider text-zinc-500">
              Medio de pago
            </p>
            <p className="text-zinc-900">
              {invoice.payment_mean_code
                ? `${paymentMeanLabels[invoice.payment_mean_code] ?? "Otros"} (${invoice.payment_mean_code})`
                : "—"}
            </p>
          </div>
        </div>

        {/* Líneas */}
        <Card>
          <CardHeader>
            <CardTitle>Líneas</CardTitle>
          </CardHeader>
          <CardContent>
            <Table
              wrapperClassName="overflow-visible"
              className="w-full text-xs"
            >
              <caption className="sr-only">Líneas de la factura</caption>
              <TableHeader>
                <TableRow>
                  <TableHead dense>Descripción</TableHead>
                  <TableHead dense className="text-right">Cantidad</TableHead>
                  <TableHead dense className="text-right">P. Unitario</TableHead>
                  <TableHead dense className="text-right">Descuento</TableHead>
                  <TableHead dense className="text-right">Impuesto</TableHead>
                  <TableHead dense className="text-right">Total</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {invoice.lines.map((line) => (
                  <TableRow key={line.id}>
                    <TableCell dense className="text-zinc-900">
                      {line.description ?? "Ítem"}
                    </TableCell>
                    <TableCell dense className="text-right tabular-nums text-zinc-900">
                      {formatQuantity(line.quantity)}
                    </TableCell>
                    <TableCell dense className="text-right tabular-nums text-zinc-900">
                      {formatCurrency(line.unit_price, invoice.currency)}
                    </TableCell>
                    <TableCell dense className="text-right tabular-nums text-zinc-900">
                      {Number(line.discount_percent).toFixed(2)} %
                    </TableCell>
                    <TableCell dense className="text-right tabular-nums text-zinc-900">
                      {formatTaxRate(line.tax_rate)}
                    </TableCell>
                    <TableCell dense className="text-right tabular-nums font-medium text-zinc-950">
                      {formatCurrency(line.line_total, invoice.currency)}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
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
              <tr
                className={`font-bold ${
                  hasPendingBalance ? "text-red-600" : "text-emerald-600"
                }`}
              >
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
              <Table
                wrapperClassName="overflow-visible"
                className="w-full text-xs"
              >
                <caption className="sr-only">Pagos de la factura</caption>
                <TableHeader>
                  <TableRow>
                    <TableHead dense>Fecha</TableHead>
                    <TableHead dense>Método</TableHead>
                    <TableHead dense>Referencia</TableHead>
                    <TableHead dense className="text-right">Monto</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {payments.map((payment) => (
                    <TableRow key={payment.id}>
                      <TableCell dense className="text-zinc-900">
                        {payment.payment_date}
                      </TableCell>
                      <TableCell dense className="text-zinc-900">
                        {payment.method}
                      </TableCell>
                      <TableCell dense className="text-zinc-900">
                        {payment.reference ?? "—"}
                      </TableCell>
                      <TableCell dense className="text-right tabular-nums text-zinc-900">
                        {formatCurrency(payment.amount, invoice.currency)}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
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
              <Table
                wrapperClassName="overflow-visible"
                className="w-full text-xs"
              >
                <caption className="sr-only">Notas crédito de la factura</caption>
                <TableHeader>
                  <TableRow>
                    <TableHead dense>Número</TableHead>
                    <TableHead dense>Fecha</TableHead>
                    <TableHead dense>Estado</TableHead>
                    <TableHead dense className="text-right">Total</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {creditNotes.map((cn) => (
                    <TableRow key={cn.id}>
                      <TableCell dense className="font-mono text-zinc-950">
                        {cn.number ?? "—"}
                      </TableCell>
                      <TableCell dense className="text-zinc-900">
                        {cn.issue_date}
                      </TableCell>
                      <TableCell dense className="text-zinc-900">
                        {cn.status === "issued" ? "Emitida" : "Borrador"}
                      </TableCell>
                      <TableCell dense className="text-right tabular-nums text-zinc-950">
                        {formatCurrency(cn.total, invoice.currency)}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        )}

        {/* Documentos DIAN (generación local, no se imprimen) */}
        <Card className="mt-8 print:hidden">
          <CardHeader>
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <CardTitle>Documento electrónico DIAN</CardTitle>
                <CardDescription>
                  XML UBL 2.1 y PDF con QR generados localmente (Fase 38A, sin
                  envío a la DIAN).
                </CardDescription>
              </div>
              <InvoiceDianBadge dianStatus={invoice.dian_status} />
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            {dianError ? (
              <p
                role="alert"
                className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700"
              >
                {dianError}
              </p>
            ) : null}
            {dianSuccess ? (
              <p
                role="status"
                className="rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700"
              >
                {dianSuccess}
              </p>
            ) : null}

            {invoice.cufe ? (
              <div>
                <p className="text-xs font-semibold uppercase tracking-wider text-zinc-500">
                  CUFE
                </p>
                <p className="mt-1 break-all font-mono text-xs text-zinc-700">
                  {invoice.cufe}
                </p>
              </div>
            ) : null}

            {isIssued ? (
              <div className="flex flex-wrap gap-2">
                <Button
                  onClick={async () => {
                    setDianError(null);
                    setDianSuccess(null);
                    setDianBusy("xml");
                    try {
                      await downloadInvoiceXml(invoice.id);
                      setDianSuccess("XML DIAN descargado.");
                    } catch (cause) {
                      setDianError(
                        cause instanceof ApiError
                          ? cause.message
                          : "No se pudo descargar el XML.",
                      );
                    } finally {
                      setDianBusy(null);
                    }
                  }}
                  disabled={dianBusy !== null}
                  className="border border-zinc-300 bg-white text-zinc-800 hover:bg-zinc-50"
                >
                  <FileCode className="mr-2 size-4" aria-hidden="true" />
                  Descargar XML
                </Button>
                <Button
                  onClick={async () => {
                    setDianError(null);
                    setDianSuccess(null);
                    setDianBusy("pdf");
                    try {
                      await downloadInvoicePdf(invoice.id);
                      setDianSuccess("PDF DIAN descargado.");
                    } catch (cause) {
                      setDianError(
                        cause instanceof ApiError
                          ? cause.message
                          : "No se pudo descargar el PDF.",
                      );
                    } finally {
                      setDianBusy(null);
                    }
                  }}
                  disabled={dianBusy !== null}
                  className="border border-zinc-300 bg-white text-zinc-800 hover:bg-zinc-50"
                >
                  <FileText className="mr-2 size-4" aria-hidden="true" />
                  Descargar PDF
                </Button>
                {canRegenerateCufe ? (
                  <Button
                    onClick={async () => {
                      setDianError(null);
                      setDianSuccess(null);
                      setDianBusy("cufe");
                      try {
                        const result = await regenerateInvoiceCufe(invoice.id);
                        setDianSuccess(
                          `CUFE recalculado (${result.dian_status ?? "—"}).`,
                        );
                      } catch (cause) {
                        setDianError(
                          cause instanceof ApiError
                            ? cause.message
                            : "No se pudo regenerar el CUFE.",
                        );
                      } finally {
                        setDianBusy(null);
                      }
                    }}
                    disabled={dianBusy !== null}
                    className="bg-violet-600 text-white hover:bg-violet-500"
                  >
                    <RefreshCw className="mr-2 size-4" aria-hidden="true" />
                    Regenerar CUFE
                  </Button>
                ) : null}
              </div>
            ) : (
              <p className="text-sm text-zinc-500">
                Los documentos DIAN se generan cuando la factura está emitida.
              </p>
            )}
          </CardContent>
        </Card>

        {/* Acciones (no se imprimen) */}
        <div className="mt-10 flex flex-wrap justify-end gap-2 print:hidden">
          <Link
            href="/invoices"
            className="inline-flex items-center justify-center gap-2 rounded-lg border border-zinc-300 bg-white px-4 py-2 text-sm font-semibold text-zinc-700 shadow-sm transition-colors hover:border-zinc-400 hover:bg-zinc-50 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-violet-500"
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
              className="bg-violet-600 text-white hover:bg-violet-500"
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
    </div>
  );
}
