"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { FileCode, FileText, Layers } from "lucide-react";

import {
  ApiError,
  calculatePayroll,
  downloadPayrollPdf,
  downloadPayrollPila,
  downloadPayrollXml,
  type PayrollPeriodStatus,
} from "@/lib/api";

const actionButtonClassName =
  "inline-flex items-center justify-center rounded-md border bg-white px-2.5 py-1 text-xs font-semibold shadow-sm transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 disabled:cursor-wait disabled:opacity-60";

interface PayrollActionsProps {
  periodId: string;
  status: PayrollPeriodStatus;
}

export function PayrollActions({ periodId, status }: PayrollActionsProps) {
  const router = useRouter();
  const [isCalculating, setIsCalculating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleCalculate(): Promise<void> {
    if (isCalculating) {
      return;
    }

    setError(null);
    setIsCalculating(true);

    try {
      await calculatePayroll(periodId);
      router.refresh();
    } catch (cause) {
      setError(
        cause instanceof ApiError
          ? cause.message
          : "No se pudo calcular la nómina. Inténtalo de nuevo.",
      );
    } finally {
      setIsCalculating(false);
    }
  }

  if (status === "CLOSED") {
    return (
      <div className="flex flex-wrap items-center justify-end gap-1">
        <button
          type="button"
          onClick={async () => {
            try {
              await downloadPayrollXml(periodId);
            } catch (cause) {
              setError(
                cause instanceof ApiError
                  ? cause.message
                  : "No se pudo descargar el XML de nómina.",
              );
            }
          }}
          className={`${actionButtonClassName} border-violet-300 text-violet-800 hover:bg-violet-50`}
        >
          <FileCode className="mr-1 size-3.5" aria-hidden="true" />
          XML Nómina
        </button>
        <button
          type="button"
          onClick={async () => {
            try {
              await downloadPayrollPdf(periodId);
            } catch (cause) {
              setError(
                cause instanceof ApiError
                  ? cause.message
                  : "No se pudo descargar el PDF de nómina.",
              );
            }
          }}
          className={`${actionButtonClassName} border-slate-300 text-slate-700 hover:bg-slate-50`}
        >
          <FileText className="mr-1 size-3.5" aria-hidden="true" />
          PDF
        </button>
        <button
          type="button"
          onClick={async () => {
            try {
              await downloadPayrollPila(periodId);
            } catch (cause) {
              setError(
                cause instanceof ApiError
                  ? cause.message
                  : "No se pudo descargar la PILA.",
              );
            }
          }}
          className={`${actionButtonClassName} border-emerald-300 text-emerald-700 hover:bg-emerald-50`}
        >
          <Layers className="mr-1 size-3.5" aria-hidden="true" />
          PILA
        </button>
        {error ? (
          <p
            role="alert"
            className="max-w-56 whitespace-normal text-right text-xs leading-4 text-red-600"
          >
            {error}
          </p>
        ) : null}
      </div>
    );
  }

  return (
    <div className="flex flex-col items-end gap-1">
      <button
        type="button"
        onClick={handleCalculate}
        disabled={isCalculating}
        aria-busy={isCalculating}
        className={`${actionButtonClassName} border-slate-300 text-slate-700 hover:border-slate-400 hover:bg-slate-50 focus-visible:outline-violet-500`}
      >
        {isCalculating ? "Calculando..." : "Calcular Nómina"}
      </button>

      {error ? (
        <p
          role="alert"
          className="max-w-56 whitespace-normal text-right text-xs leading-4 text-red-600"
        >
          {error}
        </p>
      ) : null}
    </div>
  );
}
