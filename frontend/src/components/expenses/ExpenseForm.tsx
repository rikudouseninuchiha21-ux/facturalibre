"use client";

import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";

import { Button } from "@/components/ui/button";
import { ApiError, createExpense, type ExpenseCreateInput } from "@/lib/api";

const inputClassName =
  "mt-1 block w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-950 shadow-sm outline-none transition focus:border-slate-900 focus:ring-2 focus:ring-slate-900/10 disabled:cursor-not-allowed disabled:bg-slate-50 disabled:text-slate-500";

const numberFieldClassName = `${inputClassName} tabular-nums`;

const PAYMENT_METHODS: { value: string; label: string }[] = [
  { value: "cash", label: "Efectivo" },
  { value: "transfer", label: "Transferencia bancaria" },
];

export function ExpenseForm() {
  const router = useRouter();
  const [date, setDate] = useState("");
  const [concept, setConcept] = useState("");
  const [amount, setAmount] = useState("");
  const [paymentMethod, setPaymentMethod] = useState("cash");
  const [reference, setReference] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(
    event: FormEvent<HTMLFormElement>,
  ): Promise<void> {
    event.preventDefault();

    const trimmedConcept = concept.trim();
    const trimmedAmount = amount.trim();
    const trimmedReference = reference.trim();

    if (!trimmedConcept) {
      setError("El concepto es obligatorio.");
      setSuccess(null);
      return;
    }

    const numericAmount = Number(trimmedAmount);
    if (!Number.isFinite(numericAmount) || numericAmount < 0) {
      setError("El monto debe ser un número mayor o igual a cero.");
      setSuccess(null);
      return;
    }

    setError(null);
    setSuccess(null);
    setIsSubmitting(true);

    try {
      const payload: ExpenseCreateInput = {
        date,
        concept: trimmedConcept,
        amount: trimmedAmount,
        payment_method: paymentMethod,
        ...(trimmedReference ? { reference: trimmedReference } : {}),
      };

      await createExpense(payload);

      setDate("");
      setConcept("");
      setAmount("");
      setPaymentMethod("cash");
      setReference("");
      setSuccess("Gasto registrado correctamente.");
      router.refresh();
    } catch (cause) {
      setError(
        cause instanceof ApiError
          ? `No se pudo registrar el gasto: ${cause.message}`
          : "No se pudo registrar el gasto. Revisa tu conexión e inténtalo de nuevo.",
      );
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} noValidate className="space-y-4">
      <div className="grid gap-4 sm:grid-cols-2">
        <div>
          <label
            htmlFor="expense-date"
            className="block text-sm font-medium text-slate-700"
          >
            Fecha{" "}
            <span className="text-red-600" aria-hidden="true">
              *
            </span>
          </label>
          <input
            id="expense-date"
            name="date"
            type="date"
            required
            value={date}
            onChange={(event) => setDate(event.target.value)}
            disabled={isSubmitting}
            className={inputClassName}
          />
        </div>

        <div>
          <label
            htmlFor="expense-payment-method"
            className="block text-sm font-medium text-slate-700"
          >
            Método de pago{" "}
            <span className="text-red-600" aria-hidden="true">
              *
            </span>
          </label>
          <select
            id="expense-payment-method"
            name="payment_method"
            value={paymentMethod}
            onChange={(event) =>
              setPaymentMethod(event.target.value as "cash" | "transfer")
            }
            disabled={isSubmitting}
            className={inputClassName}
          >
            {PAYMENT_METHODS.map((method) => (
              <option key={method.value} value={method.value}>
                {method.label}
              </option>
            ))}
          </select>
        </div>

        <div className="sm:col-span-2">
          <label
            htmlFor="expense-concept"
            className="block text-sm font-medium text-slate-700"
          >
            Concepto{" "}
            <span className="text-red-600" aria-hidden="true">
              *
            </span>
          </label>
          <input
            id="expense-concept"
            name="concept"
            type="text"
            required
            maxLength={200}
            autoComplete="off"
            value={concept}
            onChange={(event) => setConcept(event.target.value)}
            disabled={isSubmitting}
            className={inputClassName}
            placeholder="Ej. Arriendo de oficina"
          />
        </div>

        <div>
          <label
            htmlFor="expense-amount"
            className="block text-sm font-medium text-slate-700"
          >
            Monto{" "}
            <span className="text-red-600" aria-hidden="true">
              *
            </span>
          </label>
          <input
            id="expense-amount"
            name="amount"
            type="number"
            min="0"
            step="0.01"
            inputMode="decimal"
            required
            value={amount}
            onChange={(event) => setAmount(event.target.value)}
            disabled={isSubmitting}
            className={numberFieldClassName}
            placeholder="Ej. 1500000.00"
          />
        </div>

        <div>
          <label
            htmlFor="expense-reference"
            className="block text-sm font-medium text-slate-700"
          >
            Referencia{" "}
            <span className="text-xs font-normal text-slate-400">
              (opcional)
            </span>
          </label>
          <input
            id="expense-reference"
            name="reference"
            type="text"
            maxLength={200}
            autoComplete="off"
            value={reference}
            onChange={(event) => setReference(event.target.value)}
            disabled={isSubmitting}
            className={inputClassName}
            placeholder="Ej. Factura #12345"
          />
        </div>
      </div>

      {error ? (
        <p
          id="expense-form-error"
          role="alert"
          className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700"
        >
          {error}
        </p>
      ) : null}

      {success ? (
        <p
          role="status"
          className="rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-700"
        >
          {success}
        </p>
      ) : null}

      <div className="flex justify-end">
        <Button
          type="submit"
          disabled={isSubmitting}
          className="w-full sm:w-auto"
        >
          {isSubmitting ? "Registrando..." : "Registrar Gasto"}
        </Button>
      </div>
    </form>
  );
}
