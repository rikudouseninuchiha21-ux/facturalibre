"use client";

import { useRouter } from "next/navigation";
import { useMemo, useState } from "react";
import {
  AlertCircle,
  Bell,
  CheckCircle2,
  Clock,
  CreditCard,
  Handshake,
  Plus,
  Receipt,
  X,
} from "lucide-react";

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
import {
  ApiError,
  cancelAgreement,
  createAgreement,
  createReminder,
  payInstallment,
  type AgreementStatus,
  type CustomerAging,
  type CustomerStatement,
  type PaymentAgreement,
  type PaymentReminder,
} from "@/lib/api";
import { formatCurrency, formatDate } from "@/lib/format";

const inputClassName =
  "mt-1 block w-full rounded-lg border border-zinc-300 bg-white px-3 py-2 text-sm text-zinc-950 shadow-sm outline-none transition focus:border-amber-600 focus:ring-2 focus:ring-amber-500/10 disabled:bg-zinc-100";

const AGREEMENT_STATUS_LABELS: Record<AgreementStatus, string> = {
  ACTIVE: "Activo",
  COMPLETED: "Completado",
  BROKEN: "Incumplido",
  CANCELLED: "Cancelado",
};

const AGREEMENT_STATUS_STYLES: Record<AgreementStatus, string> = {
  ACTIVE: "bg-amber-50 text-amber-800 ring-amber-200",
  COMPLETED: "bg-emerald-50 text-emerald-700 ring-emerald-200",
  BROKEN: "bg-red-50 text-red-700 ring-red-200",
  CANCELLED: "bg-zinc-100 text-zinc-600 ring-zinc-200",
};

export interface InvoiceOption {
  id: string;
  number: string | null;
  issue_date: string;
  due_date: string;
  balance: string;
}

interface CustomerAccountClientProps {
  contactId: string;
  contactName: string;
  aging: CustomerAging;
  statement: CustomerStatement;
  reminders: PaymentReminder[];
  agreements: PaymentAgreement[];
  invoices: InvoiceOption[];
  canManage: boolean;
}

function todayIso(): string {
  return new Date().toISOString().slice(0, 10);
}

function parseCents(value: string): number {
  const normalized = value.replace(/[^0-9.]/g, "");
  const amount = Number(normalized);
  if (!Number.isFinite(amount)) return 0;
  return Math.round(amount * 100);
}

function previewInstallments(
  total: string,
  installments: number,
): string[] {
  const totalCents = parseCents(total);
  if (totalCents <= 0 || installments < 1) return [];
  const base = Math.floor(totalCents / installments);
  const amounts = Array.from({ length: installments - 1 }, () => base);
  amounts.push(totalCents - base * (installments - 1));
  return amounts.map((cents) => (cents / 100).toFixed(2));
}

function Modal({
  title,
  description,
  onClose,
  children,
}: {
  title: string;
  description: string;
  onClose: () => void;
  children: React.ReactNode;
}) {
  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center bg-zinc-950/50 p-4">
      <div
        role="dialog"
        aria-modal="true"
        aria-label={title}
        className="max-h-[90vh] w-full max-w-xl overflow-y-auto rounded-2xl border border-zinc-200 bg-white shadow-2xl"
      >
        <div className="flex items-start justify-between gap-4 border-b border-zinc-100 px-6 py-4">
          <div>
            <h2 className="text-lg font-semibold text-zinc-950">{title}</h2>
            <p className="mt-1 text-sm text-zinc-500">{description}</p>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Cerrar"
            className="rounded-lg p-1.5 text-zinc-500 transition-colors hover:bg-zinc-100 hover:text-zinc-900"
          >
            <X className="size-5" aria-hidden="true" />
          </button>
        </div>
        <div className="px-6 py-5">{children}</div>
      </div>
    </div>
  );
}

export function CustomerAccountClient({
  contactId,
  contactName,
  aging,
  statement,
  reminders,
  agreements,
  invoices,
  canManage,
}: CustomerAccountClientProps) {
  const router = useRouter();
  const [reminderOpen, setReminderOpen] = useState(false);
  const [agreementOpen, setAgreementOpen] = useState(false);
  const [payTarget, setPayTarget] = useState<{
    agreement: PaymentAgreement;
    installmentId: string;
    balance: string;
  } | null>(null);
  const [payAmount, setPayAmount] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const [reminderInvoice, setReminderInvoice] = useState(
    invoices[0]?.id ?? "",
  );
  const [reminderLevel, setReminderLevel] = useState(1);
  const [reminderNotes, setReminderNotes] = useState("");

  const [agreementInvoice, setAgreementInvoice] = useState("");
  const [agreementTotal, setAgreementTotal] = useState("");
  const [agreementInstallments, setAgreementInstallments] = useState(3);
  const [agreementStart, setAgreementStart] = useState(todayIso());
  const [agreementFrequency, setAgreementFrequency] = useState(30);
  const [agreementNotes, setAgreementNotes] = useState("");

  const preview = useMemo(
    () => previewInstallments(agreementTotal, agreementInstallments),
    [agreementTotal, agreementInstallments],
  );

  function resetMessages() {
    setError(null);
    setSuccess(null);
  }

  async function submitReminder(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    resetMessages();
    if (!reminderInvoice) {
      setError("Selecciona una factura con saldo pendiente.");
      return;
    }
    setIsSubmitting(true);
    try {
      await createReminder({
        invoice_id: reminderInvoice,
        level: reminderLevel,
        channel: "IN_APP",
        notes: reminderNotes.trim() || undefined,
      });
      setReminderOpen(false);
      setReminderNotes("");
      setSuccess("Recordatorio registrado y notificado.");
      router.refresh();
    } catch (cause) {
      setError(
        cause instanceof ApiError
          ? cause.message
          : "No se pudo registrar el recordatorio.",
      );
    } finally {
      setIsSubmitting(false);
    }
  }

  async function submitAgreement(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    resetMessages();
    if (parseCents(agreementTotal) <= 0) {
      setError("El monto total debe ser mayor que cero.");
      return;
    }
    setIsSubmitting(true);
    try {
      await createAgreement({
        contact_id: contactId,
        invoice_id: agreementInvoice || undefined,
        total_amount: agreementTotal,
        installments: agreementInstallments,
        start_date: agreementStart,
        frequency_days: agreementFrequency,
        notes: agreementNotes.trim() || undefined,
      });
      setAgreementOpen(false);
      setAgreementTotal("");
      setAgreementNotes("");
      setSuccess("Acuerdo de pago creado con sus cuotas.");
      router.refresh();
    } catch (cause) {
      setError(
        cause instanceof ApiError
          ? cause.message
          : "No se pudo crear el acuerdo de pago.",
      );
    } finally {
      setIsSubmitting(false);
    }
  }

  async function submitInstallmentPayment(
    event: React.FormEvent<HTMLFormElement>,
  ) {
    event.preventDefault();
    if (!payTarget) return;
    resetMessages();
    setIsSubmitting(true);
    try {
      await payInstallment(
        payTarget.agreement.id,
        payTarget.installmentId,
        payAmount,
      );
      setPayTarget(null);
      setPayAmount("");
      setSuccess("Abono registrado en la cuota.");
      router.refresh();
    } catch (cause) {
      setError(
        cause instanceof ApiError
          ? cause.message
          : "No se pudo registrar el abono.",
      );
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handleCancelAgreement(agreementId: string) {
    if (!window.confirm("¿Cancelar este acuerdo? Los abonos se conservan.")) {
      return;
    }
    resetMessages();
    try {
      await cancelAgreement(agreementId);
      setSuccess("Acuerdo cancelado. Los abonos registrados se conservan.");
      router.refresh();
    } catch (cause) {
      setError(
        cause instanceof ApiError
          ? cause.message
          : "No se pudo cancelar el acuerdo.",
      );
    }
  }

  return (
    <div className="space-y-6">
      {error ? (
        <div
          role="alert"
          className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700"
        >
          {error}
        </div>
      ) : null}
      {success ? (
        <div
          role="status"
          className="rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700"
        >
          {success}
        </div>
      ) : null}

      <section className="grid gap-4 md:grid-cols-3">
        <Card className="bg-gradient-to-br from-amber-50 to-white">
          <CardHeader className="pb-2 flex flex-row items-center justify-between">
            <CardDescription>Total por cobrar</CardDescription>
            <span className="flex size-9 items-center justify-center rounded-xl bg-amber-600 text-white">
              <Receipt className="size-4" aria-hidden="true" />
            </span>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold tabular-nums text-amber-950">
              {formatCurrency(aging.total)}
            </p>
            <p className="mt-1 text-sm text-zinc-500">
              {aging.invoice_count} factura
              {aging.invoice_count === 1 ? "" : "s"} con saldo.
            </p>
          </CardContent>
        </Card>
        <Card className="bg-gradient-to-br from-red-50 to-white">
          <CardHeader className="pb-2 flex flex-row items-center justify-between">
            <CardDescription>Vencido</CardDescription>
            <span className="flex size-9 items-center justify-center rounded-xl bg-red-600 text-white">
              <AlertCircle className="size-4" aria-hidden="true" />
            </span>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold tabular-nums text-red-950">
              {formatCurrency(aging.total_overdue)}
            </p>
            <p className="mt-1 text-sm text-zinc-500">
              91-120: {formatCurrency(aging.d91_120)} · 120+:{" "}
              {formatCurrency(aging.d120_plus)}
            </p>
          </CardContent>
        </Card>
        <Card className="bg-gradient-to-br from-emerald-50 to-white">
          <CardHeader className="pb-2 flex flex-row items-center justify-between">
            <CardDescription>Corriente</CardDescription>
            <span className="flex size-9 items-center justify-center rounded-xl bg-emerald-600 text-white">
              <Clock className="size-4" aria-hidden="true" />
            </span>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold tabular-nums text-emerald-950">
              {formatCurrency(aging.current)}
            </p>
            <p className="mt-1 text-sm text-zinc-500">
              0-30: {formatCurrency(aging.d0_30)} · 31-60:{" "}
              {formatCurrency(aging.d31_60)}
            </p>
          </CardContent>
        </Card>
      </section>

      {canManage ? (
        <div className="flex flex-wrap gap-3">
          <Button
            onClick={() => {
              resetMessages();
              setReminderOpen(true);
            }}
            disabled={invoices.length === 0}
          >
            <Bell className="mr-2 size-4" aria-hidden="true" />
            Enviar recordatorio
          </Button>
          <Button
            onClick={() => {
              resetMessages();
              setAgreementOpen(true);
            }}
            className="bg-zinc-900 hover:bg-zinc-800"
          >
            <Plus className="mr-2 size-4" aria-hidden="true" />
            Nuevo acuerdo de pago
          </Button>
        </div>
      ) : null}

      <Card>
        <CardHeader>
          <CardTitle>Estado de cuenta</CardTitle>
          <CardDescription>
            Movimientos del {formatDate(statement.from_date)} al{" "}
            {formatDate(statement.to_date)}. Saldo inicial{" "}
            {formatCurrency(statement.opening_balance)}.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {statement.lines.length === 0 ? (
            <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-zinc-300 bg-zinc-50 px-6 py-10 text-center">
              <Receipt className="size-9 text-amber-500" aria-hidden="true" />
              <p className="mt-2 font-semibold text-zinc-900">
                Sin movimientos en el rango
              </p>
              <p className="mt-1 text-sm text-zinc-500">
                El saldo inicial y final son {formatCurrency(statement.closing_balance)}.
              </p>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Fecha</TableHead>
                  <TableHead>Tipo</TableHead>
                  <TableHead>Referencia</TableHead>
                  <TableHead className="text-right">Débito</TableHead>
                  <TableHead className="text-right">Crédito</TableHead>
                  <TableHead className="text-right">Saldo</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {statement.lines.map((line, index) => (
                  <TableRow key={`${line.type}-${line.reference}-${index}`}>
                    <TableCell className="whitespace-nowrap text-zinc-600">
                      {formatDate(line.date)}
                    </TableCell>
                    <TableCell>
                      <span className="rounded-full bg-zinc-100 px-2 py-0.5 text-xs font-semibold text-zinc-700">
                        {line.type === "INVOICE"
                          ? "Factura"
                          : line.type === "PAYMENT"
                            ? "Pago"
                            : "Nota crédito"}
                      </span>
                    </TableCell>
                    <TableCell>
                      <p className="font-medium text-zinc-900">
                        {line.reference}
                      </p>
                      <p className="text-xs text-zinc-500">
                        {line.description}
                      </p>
                    </TableCell>
                    <TableCell className="text-right tabular-nums text-zinc-700">
                      {line.debit === "0.00" ? "—" : formatCurrency(line.debit)}
                    </TableCell>
                    <TableCell className="text-right tabular-nums text-zinc-700">
                      {line.credit === "0.00"
                        ? "—"
                        : formatCurrency(line.credit)}
                    </TableCell>
                    <TableCell className="text-right font-semibold tabular-nums text-zinc-950">
                      {formatCurrency(line.running_balance)}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
          <div className="mt-4 flex justify-end border-t border-zinc-100 pt-4">
            <p className="text-sm text-zinc-500">
              Saldo final:{" "}
              <span className="text-base font-bold tabular-nums text-zinc-950">
                {formatCurrency(statement.closing_balance)}
              </span>
            </p>
          </div>
        </CardContent>
      </Card>

      <div className="grid gap-6 xl:grid-cols-2">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <div>
              <CardTitle>Acuerdos de pago</CardTitle>
              <CardDescription>
                Renegociaciones de cartera. No generan contabilidad.
              </CardDescription>
            </div>
            <Handshake className="size-5 text-amber-600" aria-hidden="true" />
          </CardHeader>
          <CardContent className="space-y-4">
            {agreements.length === 0 ? (
              <p className="rounded-xl border border-dashed border-zinc-300 bg-zinc-50 px-4 py-6 text-center text-sm text-zinc-500">
                Sin acuerdos registrados.
              </p>
            ) : (
              agreements.map((agreement) => (
                <div
                  key={agreement.id}
                  className="rounded-xl border border-zinc-200 p-4"
                >
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div>
                      <p className="font-semibold text-zinc-900">
                        {formatCurrency(agreement.total_amount)} en{" "}
                        {agreement.installments} cuota
                        {agreement.installments === 1 ? "" : "s"}
                      </p>
                      <p className="text-xs text-zinc-500">
                        Inicio {formatDate(agreement.start_date)} · Pagado{" "}
                        {formatCurrency(agreement.paid_total)} · Saldo{" "}
                        {formatCurrency(agreement.balance)}
                      </p>
                    </div>
                    <span
                      className={`rounded-full px-2.5 py-1 text-xs font-semibold ring-1 ${AGREEMENT_STATUS_STYLES[agreement.status]}`}
                    >
                      {AGREEMENT_STATUS_LABELS[agreement.status]}
                    </span>
                  </div>

                  <ul className="mt-3 space-y-2">
                    {agreement.installment_items.map((installment) => (
                      <li
                        key={installment.id}
                        className="flex flex-wrap items-center justify-between gap-2 rounded-lg bg-zinc-50 px-3 py-2 text-sm"
                      >
                        <span className="text-zinc-600">
                          {formatDate(installment.due_date)}
                        </span>
                        <span className="tabular-nums text-zinc-700">
                          {formatCurrency(installment.paid_amount)} /{" "}
                          {formatCurrency(installment.amount)}
                        </span>
                        {canManage &&
                        agreement.status === "ACTIVE" &&
                        Number(installment.balance) > 0 ? (
                          <button
                            type="button"
                            onClick={() => {
                              resetMessages();
                              setPayTarget({
                                agreement,
                                installmentId: installment.id,
                                balance: installment.balance,
                              });
                              setPayAmount(installment.balance);
                            }}
                            className="inline-flex items-center gap-1 rounded-md px-2 py-1 text-xs font-semibold text-amber-700 hover:bg-amber-100"
                          >
                            <CreditCard className="size-3.5" aria-hidden="true" />
                            Abonar
                          </button>
                        ) : Number(installment.balance) === 0 ? (
                          <CheckCircle2
                            className="size-4 text-emerald-600"
                            aria-label="Cuota pagada"
                          />
                        ) : null}
                      </li>
                    ))}
                  </ul>

                  {canManage &&
                  (agreement.status === "ACTIVE" ||
                    agreement.status === "BROKEN") ? (
                    <button
                      type="button"
                      onClick={() => handleCancelAgreement(agreement.id)}
                      className="mt-3 text-xs font-semibold text-red-600 hover:text-red-800"
                    >
                      Cancelar acuerdo
                    </button>
                  ) : null}
                </div>
              ))
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <div>
              <CardTitle>Historial de recordatorios</CardTitle>
              <CardDescription>
                Niveles 1 a 5 con anti-spam de 24 horas por nivel.
              </CardDescription>
            </div>
            <Bell className="size-5 text-amber-600" aria-hidden="true" />
          </CardHeader>
          <CardContent>
            {reminders.length === 0 ? (
              <p className="rounded-xl border border-dashed border-zinc-300 bg-zinc-50 px-4 py-6 text-center text-sm text-zinc-500">
                Aún no se han enviado recordatorios a este cliente.
              </p>
            ) : (
              <ul className="divide-y divide-zinc-100">
                {reminders.map((reminder) => (
                  <li key={reminder.id} className="flex gap-3 py-3">
                    <span className="mt-0.5 flex size-8 shrink-0 items-center justify-center rounded-full bg-amber-100 text-xs font-bold text-amber-800">
                      {reminder.level}
                    </span>
                    <div className="min-w-0">
                      <p className="text-sm font-semibold text-zinc-900">
                        Nivel {reminder.level} · {reminder.channel}
                      </p>
                      <p className="text-xs text-zinc-500">
                        {new Date(reminder.sent_at).toLocaleString("es-CO")}
                      </p>
                      {reminder.notes ? (
                        <p className="mt-1 text-sm text-zinc-600">
                          {reminder.notes}
                        </p>
                      ) : null}
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>
      </div>

      {reminderOpen ? (
        <Modal
          title="Enviar recordatorio"
          description={`Notificación para ${contactName}. El nivel 3+ genera alerta.`}
          onClose={() => setReminderOpen(false)}
        >
          <form onSubmit={submitReminder} className="space-y-4">
            <div>
              <label
                htmlFor="reminder-invoice"
                className="text-sm font-medium text-zinc-700"
              >
                Factura
              </label>
              <select
                id="reminder-invoice"
                value={reminderInvoice}
                onChange={(event) => setReminderInvoice(event.target.value)}
                className={inputClassName}
                required
              >
                {invoices.map((invoice) => (
                  <option key={invoice.id} value={invoice.id}>
                    {invoice.number ?? invoice.id.slice(0, 8)} · vence{" "}
                    {formatDate(invoice.due_date)} ·{" "}
                    {formatCurrency(invoice.balance)}
                  </option>
                ))}
              </select>
            </div>
            <div className="grid gap-4 sm:grid-cols-2">
              <div>
                <label
                  htmlFor="reminder-level"
                  className="text-sm font-medium text-zinc-700"
                >
                  Nivel
                </label>
                <select
                  id="reminder-level"
                  value={reminderLevel}
                  onChange={(event) =>
                    setReminderLevel(Number(event.target.value))
                  }
                  className={inputClassName}
                >
                  {[1, 2, 3, 4, 5].map((level) => (
                    <option key={level} value={level}>
                      {level} · {level <= 2 ? "Suave" : level === 3 ? "Firme" : "Crítico"}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label
                  htmlFor="reminder-channel"
                  className="text-sm font-medium text-zinc-700"
                >
                  Canal
                </label>
                <select
                  id="reminder-channel"
                  value="IN_APP"
                  disabled
                  className={inputClassName}
                >
                  <option value="IN_APP">In-app</option>
                </select>
              </div>
            </div>
            <div>
              <label
                htmlFor="reminder-notes"
                className="text-sm font-medium text-zinc-700"
              >
                Notas
              </label>
              <textarea
                id="reminder-notes"
                value={reminderNotes}
                onChange={(event) => setReminderNotes(event.target.value)}
                rows={3}
                className={inputClassName}
                placeholder="Detalle de la gestión de cobranza"
              />
            </div>
            <div className="flex justify-end gap-2">
              <Button
                type="button"
                onClick={() => setReminderOpen(false)}
                className="bg-zinc-200 text-zinc-800 hover:bg-zinc-300"
              >
                Cancelar
              </Button>
              <Button type="submit" disabled={isSubmitting}>
                {isSubmitting ? "Enviando…" : "Enviar recordatorio"}
              </Button>
            </div>
          </form>
        </Modal>
      ) : null}

      {agreementOpen ? (
        <Modal
          title="Nuevo acuerdo de pago"
          description="Las cuotas se generan automáticamente; la última absorbe el redondeo."
          onClose={() => setAgreementOpen(false)}
        >
          <form onSubmit={submitAgreement} className="space-y-4">
            <div>
              <label
                htmlFor="agreement-invoice"
                className="text-sm font-medium text-zinc-700"
              >
                Factura (opcional)
              </label>
              <select
                id="agreement-invoice"
                value={agreementInvoice}
                onChange={(event) => {
                  setAgreementInvoice(event.target.value);
                  const selected = invoices.find(
                    (invoice) => invoice.id === event.target.value,
                  );
                  if (selected) setAgreementTotal(selected.balance);
                }}
                className={inputClassName}
              >
                <option value="">Acuerdo global del cliente</option>
                {invoices.map((invoice) => (
                  <option key={invoice.id} value={invoice.id}>
                    {invoice.number ?? invoice.id.slice(0, 8)} · saldo{" "}
                    {formatCurrency(invoice.balance)}
                  </option>
                ))}
              </select>
            </div>
            <div className="grid gap-4 sm:grid-cols-2">
              <div>
                <label
                  htmlFor="agreement-total"
                  className="text-sm font-medium text-zinc-700"
                >
                  Monto total
                </label>
                <input
                  id="agreement-total"
                  type="number"
                  min="0.01"
                  step="0.01"
                  value={agreementTotal}
                  onChange={(event) => setAgreementTotal(event.target.value)}
                  className={inputClassName}
                  required
                />
              </div>
              <div>
                <label
                  htmlFor="agreement-installments"
                  className="text-sm font-medium text-zinc-700"
                >
                  Cuotas
                </label>
                <input
                  id="agreement-installments"
                  type="number"
                  min={1}
                  max={120}
                  value={agreementInstallments}
                  onChange={(event) =>
                    setAgreementInstallments(Number(event.target.value))
                  }
                  className={inputClassName}
                  required
                />
              </div>
              <div>
                <label
                  htmlFor="agreement-start"
                  className="text-sm font-medium text-zinc-700"
                >
                  Fecha de inicio
                </label>
                <input
                  id="agreement-start"
                  type="date"
                  value={agreementStart}
                  onChange={(event) => setAgreementStart(event.target.value)}
                  className={inputClassName}
                  required
                />
              </div>
              <div>
                <label
                  htmlFor="agreement-frequency"
                  className="text-sm font-medium text-zinc-700"
                >
                  Frecuencia
                </label>
                <select
                  id="agreement-frequency"
                  value={agreementFrequency}
                  onChange={(event) =>
                    setAgreementFrequency(Number(event.target.value))
                  }
                  className={inputClassName}
                >
                  <option value={7}>Cada 7 días</option>
                  <option value={15}>Cada 15 días</option>
                  <option value={30}>Cada 30 días</option>
                </select>
              </div>
            </div>
            <div>
              <label
                htmlFor="agreement-notes"
                className="text-sm font-medium text-zinc-700"
              >
                Notas
              </label>
              <textarea
                id="agreement-notes"
                value={agreementNotes}
                onChange={(event) => setAgreementNotes(event.target.value)}
                rows={2}
                className={inputClassName}
              />
            </div>

            {preview.length > 0 ? (
              <div className="rounded-xl border border-amber-200 bg-amber-50 p-3">
                <p className="text-xs font-semibold uppercase tracking-wide text-amber-800">
                  Vista previa de cuotas
                </p>
                <div className="mt-2 flex flex-wrap gap-2">
                  {preview.map((amount, index) => (
                    <span
                      key={`${index}-${amount}`}
                      className="rounded-full bg-white px-2.5 py-1 text-xs font-medium tabular-nums text-amber-900 ring-1 ring-amber-200"
                    >
                      #{index + 1} · {formatCurrency(amount)}
                    </span>
                  ))}
                </div>
              </div>
            ) : null}

            <div className="flex justify-end gap-2">
              <Button
                type="button"
                onClick={() => setAgreementOpen(false)}
                className="bg-zinc-200 text-zinc-800 hover:bg-zinc-300"
              >
                Cancelar
              </Button>
              <Button type="submit" disabled={isSubmitting}>
                {isSubmitting ? "Creando…" : "Crear acuerdo"}
              </Button>
            </div>
          </form>
        </Modal>
      ) : null}

      {payTarget ? (
        <Modal
          title="Abonar a cuota"
          description={`Saldo de la cuota: ${formatCurrency(payTarget.balance)}`}
          onClose={() => setPayTarget(null)}
        >
          <form onSubmit={submitInstallmentPayment} className="space-y-4">
            <div>
              <label
                htmlFor="installment-amount"
                className="text-sm font-medium text-zinc-700"
              >
                Monto del abono
              </label>
              <input
                id="installment-amount"
                type="number"
                min="0.01"
                step="0.01"
                max={payTarget.balance}
                value={payAmount}
                onChange={(event) => setPayAmount(event.target.value)}
                className={inputClassName}
                required
              />
            </div>
            <p className="text-xs text-zinc-500">
              Este abono es de gestión. El ingreso se contabiliza cuando se
              registra el pago real de la factura.
            </p>
            <div className="flex justify-end gap-2">
              <Button
                type="button"
                onClick={() => setPayTarget(null)}
                className="bg-zinc-200 text-zinc-800 hover:bg-zinc-300"
              >
                Cancelar
              </Button>
              <Button type="submit" disabled={isSubmitting}>
                {isSubmitting ? "Guardando…" : "Registrar abono"}
              </Button>
            </div>
          </form>
        </Modal>
      ) : null}
    </div>
  );
}
