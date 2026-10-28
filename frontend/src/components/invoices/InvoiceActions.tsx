"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import {
  ApiError,
  issueInvoice,
  voidInvoice,
  type LifecycleStatus,
} from "@/lib/api";

import { PaymentForm } from "./PaymentForm";

const actionButtonClassName =
  "inline-flex items-center justify-center rounded-md border bg-white px-2.5 py-1 text-xs font-semibold shadow-sm transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 disabled:cursor-wait disabled:opacity-60";

interface InvoiceActionsProps {
  invoiceId: string;
  status: LifecycleStatus;
  balance: string;
  currency: string;
}

export function InvoiceActions({
  invoiceId,
  status,
  balance,
  currency,
}: InvoiceActionsProps) {
  const router = useRouter();
  const [pendingAction, setPendingAction] = useState<
    "issue" | "void" | null
  >(null);
  const [error, setError] = useState<string | null>(null);
  const [isPaymentOpen, setIsPaymentOpen] = useState(false);

  const isPending = pendingAction !== null;
  const canRegisterPayment = status === "issued" && Number(balance) > 0;

  async function handleIssue(): Promise<void> {
    if (isPending) {
      return;
    }

    setError(null);
    setPendingAction("issue");

    try {
      await issueInvoice(invoiceId);
      router.refresh();
    } catch (cause) {
      setError(
        cause instanceof ApiError
          ? cause.message
          : "No se pudo emitir la factura. Inténtalo de nuevo.",
      );
    } finally {
      setPendingAction(null);
    }
  }

  async function handleVoid(): Promise<void> {
    if (isPending) {
      return;
    }

    setError(null);
    const reason = window.prompt(
      "Motivo de anulación de la factura (obligatorio):",
    );

    if (reason === null) {
      return;
    }

    const trimmedReason = reason.trim();

    if (!trimmedReason) {
      setError("El motivo de anulación es obligatorio.");
      return;
    }

    if (trimmedReason.length > 500) {
      setError("El motivo no puede superar los 500 caracteres.");
      return;
    }

    setPendingAction("void");

    try {
      await voidInvoice(invoiceId, { reason: trimmedReason });
      router.refresh();
    } catch (cause) {
      setError(
        cause instanceof ApiError
          ? cause.message
          : "No se pudo anular la factura. Inténtalo de nuevo.",
      );
    } finally {
      setPendingAction(null);
    }
  }

  if (status === "void") {
    return <span className="text-xs text-slate-400">—</span>;
  }

  return (
    <>
      <div className="flex flex-col items-end gap-1">
        <div className="flex flex-wrap justify-end gap-1">
          {status === "draft" ? (
            <button
              type="button"
              onClick={handleIssue}
              disabled={isPending}
              aria-busy={pendingAction === "issue"}
              className={`${actionButtonClassName} border-slate-300 text-slate-700 hover:border-slate-400 hover:bg-slate-50 focus-visible:outline-violet-500`}
            >
              {pendingAction === "issue" ? "Emitiendo..." : "Emitir"}
            </button>
          ) : (
            <>
              {canRegisterPayment ? (
                <button
                  type="button"
                  onClick={() => {
                    setError(null);
                    setIsPaymentOpen(true);
                  }}
                  disabled={isPending}
                  className={`${actionButtonClassName} border-emerald-200 text-emerald-700 hover:border-emerald-300 hover:bg-emerald-50 focus-visible:outline-emerald-600`}
                >
                  Registrar Pago
                </button>
              ) : null}
              <button
                type="button"
                onClick={handleVoid}
                disabled={isPending}
                aria-busy={pendingAction === "void"}
                className={`${actionButtonClassName} border-red-200 text-red-700 hover:border-red-300 hover:bg-red-50 focus-visible:outline-red-600`}
              >
                {pendingAction === "void" ? "Anulando..." : "Anular"}
              </button>
            </>
          )}
        </div>

        {error ? (
          <p
            role="alert"
            className="max-w-56 whitespace-normal text-right text-xs leading-4 text-red-600"
          >
            {error}
          </p>
        ) : null}
      </div>

      {isPaymentOpen ? (
        <PaymentForm
          invoiceId={invoiceId}
          balance={balance}
          currency={currency}
          onClose={() => setIsPaymentOpen(false)}
        />
      ) : null}
    </>
  );
}
