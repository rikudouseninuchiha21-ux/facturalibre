"use client";

import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";

import { Button } from "@/components/ui/button";
import { ApiError, createPayrollPeriod } from "@/lib/api";
import { formatMonth } from "@/lib/format";

const inputClassName =
  "mt-1 block w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-950 shadow-sm outline-none transition focus:border-slate-900 focus:ring-2 focus:ring-slate-900/10 disabled:cursor-not-allowed disabled:bg-slate-50 disabled:text-slate-500";

const monthOptions = Array.from({ length: 12 }, (_, index) => index + 1);

interface PayrollFormProps {
  defaultMonth: number;
  defaultYear: number;
}

export function PayrollForm({ defaultMonth, defaultYear }: PayrollFormProps) {
  const router = useRouter();
  const [month, setMonth] = useState(String(defaultMonth));
  const [year, setYear] = useState(String(defaultYear));
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(
    event: FormEvent<HTMLFormElement>,
  ): Promise<void> {
    event.preventDefault();

    const monthNumber = Number(month);
    const yearNumber = Number(year);

    if (
      !Number.isInteger(monthNumber) ||
      monthNumber < 1 ||
      monthNumber > 12
    ) {
      setError("Selecciona un mes válido.");
      setSuccess(null);
      return;
    }

    if (!Number.isInteger(yearNumber) || yearNumber < 2000 || yearNumber > 2100) {
      setError("El año debe ser un número entre 2000 y 2100.");
      setSuccess(null);
      return;
    }

    setError(null);
    setSuccess(null);
    setIsSubmitting(true);

    try {
      await createPayrollPeriod({ month: monthNumber, year: yearNumber });
      setMonth(String(defaultMonth));
      setYear(String(defaultYear));
      setSuccess("Periodo de nómina creado correctamente.");
      router.refresh();
    } catch (cause) {
      setError(
        cause instanceof ApiError
          ? `No se pudo crear el periodo: ${cause.message}`
          : "No se pudo crear el periodo. Revisa tu conexión e inténtalo de nuevo.",
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
            htmlFor="payroll-month"
            className="block text-sm font-medium text-slate-700"
          >
            Mes{" "}
            <span className="text-red-600" aria-hidden="true">
              *
            </span>
          </label>
          <select
            id="payroll-month"
            name="month"
            required
            value={month}
            onChange={(event) => setMonth(event.target.value)}
            disabled={isSubmitting}
            className={inputClassName}
          >
            {monthOptions.map((monthNumber) => (
              <option key={monthNumber} value={monthNumber}>
                {formatMonth(monthNumber)}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label
            htmlFor="payroll-year"
            className="block text-sm font-medium text-slate-700"
          >
            Año{" "}
            <span className="text-red-600" aria-hidden="true">
              *
            </span>
          </label>
          <input
            id="payroll-year"
            name="year"
            type="number"
            required
            min="2000"
            max="2100"
            step="1"
            inputMode="numeric"
            value={year}
            onChange={(event) => setYear(event.target.value)}
            disabled={isSubmitting}
            className={inputClassName}
          />
        </div>
      </div>

      {error ? (
        <p
          id="payroll-form-error"
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
          {isSubmitting ? "Creando..." : "Crear Periodo"}
        </Button>
      </div>
    </form>
  );
}
