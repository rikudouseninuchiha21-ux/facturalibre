"use client";

import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";

import { Button } from "@/components/ui/button";
import { ApiError, createTax } from "@/lib/api";

const inputClassName =
  "mt-1 block w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-950 shadow-sm outline-none transition focus:border-violet-500 focus:ring-2 focus:ring-violet-500/20 disabled:cursor-not-allowed disabled:bg-slate-50 disabled:text-slate-500";

const ratePattern = /^\d+(\.\d{1,4})?$/;

export function TaxForm() {
  const router = useRouter();
  const [name, setName] = useState("");
  const [rate, setRate] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(
    event: FormEvent<HTMLFormElement>,
  ): Promise<void> {
    event.preventDefault();

    const trimmedName = name.trim();
    const trimmedRate = rate.trim();

    if (!trimmedName) {
      setError("El nombre es obligatorio.");
      setSuccess(null);
      return;
    }

    const numericRate = Number(trimmedRate);
    if (
      !ratePattern.test(trimmedRate) ||
      !Number.isFinite(numericRate) ||
      numericRate < 0 ||
      numericRate > 100
    ) {
      setError(
        "La tasa debe ser un número entre 0 y 100, con hasta 4 decimales.",
      );
      setSuccess(null);
      return;
    }

    setError(null);
    setSuccess(null);
    setIsSubmitting(true);

    try {
      await createTax({ name: trimmedName, rate: trimmedRate });

      setName("");
      setRate("");
      setSuccess("Impuesto creado correctamente.");
      router.refresh();
    } catch (cause) {
      setError(
        cause instanceof ApiError
          ? `No se pudo crear el impuesto: ${cause.message}`
          : "No se pudo crear el impuesto. Revisa tu conexión e inténtalo de nuevo.",
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
            htmlFor="tax-name"
            className="block text-sm font-medium text-slate-700"
          >
            Nombre{" "}
            <span className="text-red-600" aria-hidden="true">
              *
            </span>
          </label>
          <input
            id="tax-name"
            name="name"
            type="text"
            required
            maxLength={100}
            autoComplete="off"
            value={name}
            onChange={(event) => setName(event.target.value)}
            disabled={isSubmitting}
            className={inputClassName}
            placeholder="Ej. IVA 19%"
          />
        </div>

        <div>
          <label
            htmlFor="tax-rate"
            className="block text-sm font-medium text-slate-700"
          >
            Tasa (%){" "}
            <span className="text-red-600" aria-hidden="true">
              *
            </span>
          </label>
          <input
            id="tax-rate"
            name="rate"
            type="number"
            required
            min="0"
            max="100"
            step="0.0001"
            inputMode="decimal"
            value={rate}
            onChange={(event) => setRate(event.target.value)}
            disabled={isSubmitting}
            className={`${inputClassName} tabular-nums`}
            placeholder="Ej. 19.00"
          />
          <p className="mt-1 text-xs text-slate-500">
            Valor entre 0 y 100, con hasta 4 decimales.
          </p>
        </div>
      </div>

      {error ? (
        <p
          id="tax-form-error"
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
          {isSubmitting ? "Creando..." : "Crear Impuesto"}
        </Button>
      </div>
    </form>
  );
}
