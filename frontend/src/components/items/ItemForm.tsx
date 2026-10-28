"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";

import { Button } from "@/components/ui/button";
import { ApiError, createItem, type Tax } from "@/lib/api";
import { formatTaxRate } from "@/lib/format";

const inputClassName =
  "mt-1 block w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-950 shadow-sm outline-none transition focus:border-violet-500 focus:ring-2 focus:ring-violet-500/20 disabled:cursor-not-allowed disabled:bg-slate-50 disabled:text-slate-500";

const pricePattern = /^\d+(\.\d{1,2})?$/;

interface ItemFormProps {
  taxes: Tax[];
}

export function ItemForm({ taxes }: ItemFormProps) {
  const router = useRouter();
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [unitPrice, setUnitPrice] = useState("");
  const [taxId, setTaxId] = useState("");
  const [priceIncludesTax, setPriceIncludesTax] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(
    event: FormEvent<HTMLFormElement>,
  ): Promise<void> {
    event.preventDefault();

    const trimmedName = name.trim();
    const trimmedDescription = description.trim();
    const trimmedUnitPrice = unitPrice.trim();

    if (!trimmedName) {
      setError("El nombre es obligatorio.");
      setSuccess(null);
      return;
    }

    const numericPrice = Number(trimmedUnitPrice);
    if (
      !pricePattern.test(trimmedUnitPrice) ||
      !Number.isFinite(numericPrice) ||
      numericPrice < 0
    ) {
      setError(
        "El precio unitario debe ser un número mayor o igual a cero, con hasta 2 decimales.",
      );
      setSuccess(null);
      return;
    }

    setError(null);
    setSuccess(null);
    setIsSubmitting(true);

    try {
      await createItem({
        name: trimmedName,
        ...(trimmedDescription ? { description: trimmedDescription } : {}),
        unit_price: trimmedUnitPrice,
        ...(taxId ? { tax_id: taxId } : {}),
        price_includes_tax: priceIncludesTax,
      });

      setName("");
      setDescription("");
      setUnitPrice("");
      setTaxId("");
      setPriceIncludesTax(false);
      setSuccess("Ítem creado correctamente.");
      router.refresh();
    } catch (cause) {
      setError(
        cause instanceof ApiError
          ? `No se pudo crear el ítem: ${cause.message}`
          : "No se pudo crear el ítem. Revisa tu conexión e inténtalo de nuevo.",
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
            htmlFor="item-name"
            className="block text-sm font-medium text-slate-700"
          >
            Nombre{" "}
            <span className="text-red-600" aria-hidden="true">
              *
            </span>
          </label>
          <input
            id="item-name"
            name="name"
            type="text"
            required
            maxLength={200}
            autoComplete="off"
            value={name}
            onChange={(event) => setName(event.target.value)}
            disabled={isSubmitting}
            className={inputClassName}
            placeholder="Ej. Servicio de consultoría"
          />
        </div>

        <div>
          <label
            htmlFor="item-unit-price"
            className="block text-sm font-medium text-slate-700"
          >
            Precio unitario{" "}
            <span className="text-red-600" aria-hidden="true">
              *
            </span>
          </label>
          <input
            id="item-unit-price"
            name="unit_price"
            type="number"
            required
            min="0"
            step="0.01"
            inputMode="decimal"
            value={unitPrice}
            onChange={(event) => setUnitPrice(event.target.value)}
            disabled={isSubmitting}
            className={`${inputClassName} tabular-nums`}
            placeholder="Ej. 150000.00"
          />
        </div>

        <div className="sm:col-span-2">
          <label
            htmlFor="item-description"
            className="block text-sm font-medium text-slate-700"
          >
            Descripción{" "}
            <span className="text-xs font-normal text-slate-400">
              (opcional)
            </span>
          </label>
          <textarea
            id="item-description"
            name="description"
            rows={3}
            value={description}
            onChange={(event) => setDescription(event.target.value)}
            disabled={isSubmitting}
            className={inputClassName}
            placeholder="Detalle del producto o servicio"
          />
        </div>

        <div className="sm:col-span-2">
          <label
            htmlFor="item-tax"
            className="block text-sm font-medium text-slate-700"
          >
            Impuesto{" "}
            <span className="text-xs font-normal text-slate-400">
              (opcional)
            </span>
          </label>
          <select
            id="item-tax"
            name="tax_id"
            value={taxId}
            onChange={(event) => setTaxId(event.target.value)}
            disabled={isSubmitting}
            className={inputClassName}
          >
            <option value="">Ninguno</option>
            {taxes.map((tax) => (
              <option key={tax.id} value={tax.id}>
                {tax.name} ({formatTaxRate(tax.rate)})
              </option>
            ))}
          </select>
          {taxes.length === 0 ? (
            <p className="mt-1 text-xs text-slate-500">
              No hay impuestos registrados. Puedes crear el ítem sin impuesto o{" "}
              <Link
                href="/taxes"
                className="font-semibold text-violet-600 underline decoration-violet-300 underline-offset-2 hover:text-violet-700"
              >
                crear un impuesto
              </Link>
              .
            </p>
          ) : null}
        </div>

        <div className="sm:col-span-2">
          <div className="flex items-center gap-2">
            <input
              id="item-price-includes-tax"
              name="price_includes_tax"
              type="checkbox"
              checked={priceIncludesTax}
              onChange={(event) => setPriceIncludesTax(event.target.checked)}
              disabled={isSubmitting}
              className="rounded border-slate-300 bg-slate-50 text-violet-600 focus:ring-violet-600 focus:ring-1"
            />
            <label
              htmlFor="item-price-includes-tax"
              className="text-sm font-medium text-slate-700"
            >
              El precio incluye IVA
              <span className="text-xs font-normal text-slate-400">
                (si está activo, el precio unitario ya tiene el impuesto incluido)
              </span>
            </label>
          </div>
        </div>
      </div>

      {error ? (
        <p
          id="item-form-error"
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
          {isSubmitting ? "Creando..." : "Crear Ítem"}
        </Button>
      </div>
    </form>
  );
}
