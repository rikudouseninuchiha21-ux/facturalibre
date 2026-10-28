"use client";

import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";

import { Button } from "@/components/ui/button";
import { ApiError, createWarehouse } from "@/lib/api";

const inputClassName =
  "mt-1 block w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-950 shadow-sm outline-none transition focus:border-violet-500 focus:ring-2 focus:ring-violet-500/20 disabled:cursor-not-allowed disabled:bg-slate-50 disabled:text-slate-500";

export function WarehouseForm() {
  const router = useRouter();
  const [name, setName] = useState("");
  const [code, setCode] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(
    event: FormEvent<HTMLFormElement>,
  ): Promise<void> {
    event.preventDefault();

    const trimmedName = name.trim();
    const trimmedCode = code.trim();

    if (!trimmedName) {
      setError("El nombre es obligatorio.");
      setSuccess(null);
      return;
    }

    if (!trimmedCode) {
      setError("El código es obligatorio.");
      setSuccess(null);
      return;
    }

    setError(null);
    setSuccess(null);
    setIsSubmitting(true);

    try {
      await createWarehouse({ name: trimmedName, code: trimmedCode });
      setName("");
      setCode("");
      setSuccess("Bodega creada correctamente.");
      router.refresh();
    } catch (cause) {
      setError(
        cause instanceof ApiError
          ? `No se pudo crear la bodega: ${cause.message}`
          : "No se pudo crear la bodega. Revisa tu conexión e inténtalo de nuevo.",
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
            htmlFor="warehouse-name"
            className="block text-sm font-medium text-slate-700"
          >
            Nombre{" "}
            <span className="text-red-600" aria-hidden="true">
              *
            </span>
          </label>
          <input
            id="warehouse-name"
            name="name"
            type="text"
            required
            maxLength={200}
            autoComplete="organization"
            value={name}
            onChange={(event) => setName(event.target.value)}
            disabled={isSubmitting}
            className={inputClassName}
            placeholder="Ej. Bodega principal"
          />
        </div>

        <div>
          <label
            htmlFor="warehouse-code"
            className="block text-sm font-medium text-slate-700"
          >
            Código{" "}
            <span className="text-red-600" aria-hidden="true">
              *
            </span>
          </label>
          <input
            id="warehouse-code"
            name="code"
            type="text"
            required
            maxLength={50}
            autoComplete="off"
            value={code}
            onChange={(event) => setCode(event.target.value.toUpperCase())}
            disabled={isSubmitting}
            className={`${inputClassName} font-mono uppercase`}
            placeholder="Ej. PRINCIPAL"
          />
        </div>
      </div>

      {error ? (
        <p
          id="warehouse-form-error"
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
          {isSubmitting ? "Creando..." : "Crear Bodega"}
        </Button>
      </div>
    </form>
  );
}
