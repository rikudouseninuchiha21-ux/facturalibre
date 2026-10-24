"use client";

import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";

import { Button } from "@/components/ui/button";
import { ApiError, createContact, type ContactCreateInput } from "@/lib/api";

const inputClassName =
  "mt-1 block w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-950 shadow-sm outline-none transition focus:border-slate-900 focus:ring-2 focus:ring-slate-900/10 disabled:cursor-not-allowed disabled:bg-slate-50 disabled:text-slate-500";

const CONTACT_TYPES: { value: string; label: string }[] = [
  { value: "customer", label: "Cliente" },
  { value: "supplier", label: "Proveedor" },
  { value: "both", label: "Ambos" },
];

const CONTACT_STATUSES: { value: string; label: string }[] = [
  { value: "LEAD", label: "Prospecto (Lead)" },
  { value: "PROSPECT", label: "Cliente Potencial" },
  { value: "CUSTOMER", label: "Cliente" },
];

export function ContactForm() {
  const router = useRouter();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [taxId, setTaxId] = useState("");
  const [type, setType] = useState<"customer" | "supplier" | "both">("customer");
  const [status, setStatus] = useState<"LEAD" | "PROSPECT" | "CUSTOMER">("CUSTOMER");
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(
    event: FormEvent<HTMLFormElement>,
  ): Promise<void> {
    event.preventDefault();

    const trimmedName = name.trim();
    if (!trimmedName) {
      setError("El nombre es obligatorio.");
      setSuccess(null);
      return;
    }

    setError(null);
    setSuccess(null);
    setIsSubmitting(true);

    try {
      const payload: ContactCreateInput = {
        name: trimmedName,
        ...(email.trim() ? { email: email.trim() } : {}),
        ...(taxId.trim() ? { tax_id: taxId.trim() } : {}),
        type,
        status,
      };

      await createContact(payload);

      setName("");
      setEmail("");
      setTaxId("");
      setType("customer");
      setStatus("CUSTOMER");
      setSuccess("Contacto creado correctamente.");
      router.refresh();
    } catch (cause) {
      setError(
        cause instanceof ApiError
          ? `No se pudo crear el contacto: ${cause.message}`
          : "No se pudo crear el contacto. Revisa tu conexión e inténtalo de nuevo.",
      );
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} noValidate className="space-y-4">
      <div className="grid gap-4 sm:grid-cols-2">
        <div className="sm:col-span-2">
          <label
            htmlFor="contact-name"
            className="block text-sm font-medium text-slate-700"
          >
            Nombre{" "}
            <span className="text-red-600" aria-hidden="true">
              *
            </span>
          </label>
          <input
            id="contact-name"
            name="name"
            type="text"
            required
            maxLength={200}
            autoComplete="organization"
            value={name}
            onChange={(event) => setName(event.target.value)}
            disabled={isSubmitting}
            className={inputClassName}
            placeholder="Ej. Comercializadora Andina S.A.S."
          />
        </div>

        <div>
          <label
            htmlFor="contact-type"
            className="block text-sm font-medium text-slate-700"
          >
            Tipo{" "}
            <span className="text-xs font-normal text-slate-400">
              (opcional)
            </span>
          </label>
          <select
            id="contact-type"
            name="type"
            value={type}
            onChange={(event) =>
              setType(event.target.value as "customer" | "supplier" | "both")
            }
            disabled={isSubmitting}
            className={inputClassName}
          >
            {CONTACT_TYPES.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label
            htmlFor="contact-status"
            className="block text-sm font-medium text-slate-700"
          >
            Estado{" "}
            <span className="text-xs font-normal text-slate-400">
              (estado comercial)
            </span>
          </label>
          <select
            id="contact-status"
            name="status"
            value={status}
            onChange={(event) =>
              setStatus(event.target.value as "LEAD" | "PROSPECT" | "CUSTOMER")
            }
            disabled={isSubmitting}
            className={inputClassName}
          >
            {CONTACT_STATUSES.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label
            htmlFor="contact-email"
            className="block text-sm font-medium text-slate-700"
          >
            Email{" "}
            <span className="text-xs font-normal text-slate-400">
              (opcional)
            </span>
          </label>
          <input
            id="contact-email"
            name="email"
            type="email"
            maxLength={254}
            autoComplete="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            disabled={isSubmitting}
            className={inputClassName}
            placeholder="contacto@empresa.com"
          />
        </div>

        <div>
          <label
            htmlFor="contact-tax-id"
            className="block text-sm font-medium text-slate-700"
          >
            NIT / Tax ID{" "}
            <span className="text-xs font-normal text-slate-400">
              (opcional)
            </span>
          </label>
          <input
            id="contact-tax-id"
            name="tax_id"
            type="text"
            maxLength={30}
            autoComplete="off"
            value={taxId}
            onChange={(event) => setTaxId(event.target.value)}
            disabled={isSubmitting}
            className={inputClassName}
            placeholder="900123456"
          />
        </div>
      </div>

      {error ? (
        <p
          id="contact-form-error"
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
          {isSubmitting ? "Creando..." : "Crear Contacto"}
        </Button>
      </div>
    </form>
  );
}
