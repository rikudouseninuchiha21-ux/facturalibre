"use client";

import { useRouter } from "next/navigation";
import { useEffect, useRef, useState, type FormEvent } from "react";

import { Button } from "@/components/ui/button";
import {
  ApiError,
  createPurchasePayment,
  type PurchasePaymentCreateInput,
} from "@/lib/api";
import { formatCurrency } from "@/lib/format";

const inputClassName =
  "mt-1 block w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-950 shadow-sm outline-none transition focus:border-violet-500 focus:ring-2 focus:ring-violet-500/20 disabled:cursor-not-allowed disabled:bg-slate-50 disabled:text-slate-500";

const amountPattern = /^\d+(\.\d{1,2})?$/;

interface PurchasePaymentFormProps {
  purchaseId: string;
  balance: string;
  currency: string;
  onClose: () => void;
}

function getTodayIsoDate(): string {
  const now = new Date();
  const year = now.getFullYear();
  const month = String(now.getMonth() + 1).padStart(2, "0");
  const day = String(now.getDate()).padStart(2, "0");

  return `${year}-${month}-${day}`;
}

export function PurchasePaymentForm({
  purchaseId,
  balance,
  currency,
  onClose,
}: PurchasePaymentFormProps) {
  const router = useRouter();
  const [amount, setAmount] = useState(balance);
  const [method, setMethod] = useState("Transferencia");
  const [reference, setReference] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const idempotencyKeyRef = useRef<string | null>(null);
  const titleId = `purchase-payment-title-${purchaseId}`;

  useEffect(() => {
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";

    function handleKeyDown(event: KeyboardEvent): void {
      if (event.key === "Escape" && !isSubmitting) {
        onClose();
      }
    }

    window.addEventListener("keydown", handleKeyDown);

    return () => {
      window.removeEventListener("keydown", handleKeyDown);
      document.body.style.overflow = previousOverflow;
    };
  }, [isSubmitting, onClose]);

  function markFormChanged(): void {
    idempotencyKeyRef.current = null;
    setError(null);
  }

  async function handleSubmit(
    event: FormEvent<HTMLFormElement>,
  ): Promise<void> {
    event.preventDefault();

    if (isSubmitting) {
      return;
    }

    const trimmedAmount = amount.trim();
    const numericAmount = Number(trimmedAmount);

    if (
      !amountPattern.test(trimmedAmount) ||
      !Number.isFinite(numericAmount) ||
      numericAmount <= 0
    ) {
      setError(
        "El monto debe ser un número mayor que cero, con hasta 2 decimales.",
      );
      return;
    }

    setError(null);
    setIsSubmitting(true);

    try {
      const idempotencyKey =
        idempotencyKeyRef.current ?? crypto.randomUUID();
      idempotencyKeyRef.current = idempotencyKey;

      const trimmedReference = reference.trim();
      const payload: PurchasePaymentCreateInput = {
        amount: trimmedAmount,
        payment_date: getTodayIsoDate(),
        method,
        ...(trimmedReference ? { reference: trimmedReference } : {}),
      };

      await createPurchasePayment(purchaseId, payload, idempotencyKey);
      idempotencyKeyRef.current = null;
      router.refresh();
      onClose();
    } catch (cause) {
      setError(
        cause instanceof ApiError
          ? `No se pudo registrar el pago: ${cause.message}`
          : "No se pudo registrar el pago. Revisa tu conexión e inténtalo de nuevo.",
      );
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/50 p-4"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget && !isSubmitting) {
          onClose();
        }
      }}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        className="w-full max-w-lg rounded-2xl border border-slate-200 bg-white p-6 shadow-2xl"
      >
        <div className="flex items-start justify-between gap-4">
          <div>
            <h2
              id={titleId}
              className="text-lg font-semibold tracking-tight text-slate-950"
            >
              Registrar Pago a Proveedor
            </h2>
            <p className="mt-1 text-sm text-slate-500">
              Registra un abono total o parcial sobre la factura de compra.
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            disabled={isSubmitting}
            aria-label="Cerrar modal de pago"
            className="rounded-md p-1 text-xl leading-none text-slate-400 transition-colors hover:bg-slate-100 hover:text-slate-700 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-violet-500 disabled:cursor-not-allowed disabled:opacity-50"
          >
            ×
          </button>
        </div>

        <div className="mt-4 flex items-center justify-between gap-4 rounded-xl bg-slate-50 px-4 py-3">
          <span className="text-sm font-medium text-slate-600">
            Saldo pendiente
          </span>
          <span className="text-lg font-semibold tabular-nums text-slate-950">
            {formatCurrency(balance, currency)}
          </span>
        </div>

        <form onSubmit={handleSubmit} noValidate className="mt-5 space-y-4">
          <div>
            <label
              htmlFor="purchase-payment-amount"
              className="block text-sm font-medium text-slate-700"
            >
              Monto a pagar{" "}
              <span className="text-red-600" aria-hidden="true">
                *
              </span>
            </label>
            <input
              id="purchase-payment-amount"
              name="amount"
              type="number"
              required
              min="0.01"
              max={balance}
              step="0.01"
              inputMode="decimal"
              autoFocus
              value={amount}
              onChange={(event) => {
                markFormChanged();
                setAmount(event.target.value);
              }}
              disabled={isSubmitting}
              className={`${inputClassName} tabular-nums`}
            />
            <p className="mt-1 text-xs text-slate-500">
              Por defecto se propone el saldo completo; puedes modificarlo para
              registrar un abono parcial.
            </p>
          </div>

          <div>
            <label
              htmlFor="purchase-payment-method"
              className="block text-sm font-medium text-slate-700"
            >
              Método de pago{" "}
              <span className="text-red-600" aria-hidden="true">
                *
              </span>
            </label>
            <select
              id="purchase-payment-method"
              name="method"
              required
              value={method}
              onChange={(event) => {
                markFormChanged();
                setMethod(event.target.value);
              }}
              disabled={isSubmitting}
              className={inputClassName}
            >
              <option value="Efectivo">Efectivo</option>
              <option value="Transferencia">Transferencia</option>
              <option value="Tarjeta">Tarjeta</option>
            </select>
          </div>

          <div>
            <label
              htmlFor="purchase-payment-reference"
              className="block text-sm font-medium text-slate-700"
            >
              Referencia{" "}
              <span className="text-xs font-normal text-slate-400">
                (opcional)
              </span>
            </label>
            <input
              id="purchase-payment-reference"
              name="reference"
              type="text"
              maxLength={100}
              autoComplete="off"
              value={reference}
              onChange={(event) => {
                markFormChanged();
                setReference(event.target.value);
              }}
              disabled={isSubmitting}
              className={inputClassName}
              placeholder="Ej. Transferencia 123456"
            />
          </div>

          {error ? (
            <p
              id="purchase-payment-form-error"
              role="alert"
              className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700"
            >
              {error}
            </p>
          ) : null}

          <div className="flex flex-col-reverse gap-3 pt-2 sm:flex-row sm:justify-end">
            <button
              type="button"
              onClick={onClose}
              disabled={isSubmitting}
              className="inline-flex items-center justify-center rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 shadow-sm transition-colors hover:border-slate-400 hover:bg-slate-50 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-violet-500 disabled:cursor-not-allowed disabled:opacity-50"
            >
              Cancelar
            </button>
            <Button
              type="submit"
              disabled={isSubmitting}
              aria-describedby={error ? "purchase-payment-form-error" : undefined}
            >
              {isSubmitting ? "Registrando..." : "Confirmar Pago"}
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}
