"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { ApiError, updateCompanySettings, type CompanySetting } from "@/lib/api";

const inputClassName =
  "mt-1 block w-full rounded-lg border border-zinc-300 bg-white px-3 py-2 text-sm text-zinc-950 shadow-sm outline-none transition focus:border-indigo-600 focus:ring-2 focus:ring-indigo-500/10 disabled:cursor-not-allowed disabled:bg-zinc-50 disabled:text-zinc-500";

interface SettingsFormProps {
  companySettings: CompanySetting;
  onClose?: () => void;
}

export function SettingsForm({
  companySettings,
  onClose,
}: SettingsFormProps) {
  const router = useRouter();
  const [name, setName] = useState(companySettings.name ?? "");
  const [taxId, setTaxId] = useState(companySettings.tax_id ?? "");
  const [address, setAddress] = useState(companySettings.address ?? "");
  const [phone, setPhone] = useState(companySettings.phone ?? "");
  const [email, setEmail] = useState(companySettings.email ?? "");
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(
    event: React.FormEvent<HTMLFormElement>,
  ): Promise<void> {
    event.preventDefault();

    setError(null);
    setSuccess(null);
    setIsSubmitting(true);

    try {
      await updateCompanySettings({
        name: name.trim() || companySettings.name,
        tax_id: taxId.trim() || undefined,
        address: address.trim() || undefined,
        phone: phone.trim() || undefined,
        email: email.trim() || undefined,
      });

      setSuccess("Configuración actualizada correctamente.");
      setTimeout(() => {
        onClose?.();
        router.refresh();
      }, 1500);
    } catch (cause) {
      setError(
        cause instanceof ApiError
          ? cause.message
          : "No se pudo actualizar la configuración. Inténtalo de nuevo.",
      );
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      <div className="grid gap-6 md:grid-cols-2">
        <div className="space-y-2">
          <label
            htmlFor="company-name"
            className="block text-sm font-medium text-zinc-700"
          >
            Nombre de la Empresa{" "}
            <span className="text-red-600" aria-hidden="true">
              *
            </span>
          </label>
          <input
            id="company-name"
            name="name"
            type="text"
            required
            maxLength={200}
            value={name}
            onChange={(event) => setName(event.target.value)}
            disabled={isSubmitting}
            className={inputClassName}
            placeholder="Nombre de tu empresa"
          />
        </div>

        <div className="space-y-2">
          <label htmlFor="company-tax-id" className="block text-sm font-medium text-zinc-700">
            NIT / Tax ID
          </label>
          <input
            id="company-tax-id"
            name="tax_id"
            type="text"
            maxLength={30}
            value={taxId}
            onChange={(event) => setTaxId(event.target.value)}
            disabled={isSubmitting}
            className={inputClassName}
            placeholder="900123456-1"
          />
        </div>

        <div className="space-y-2">
          <label htmlFor="company-address" className="block text-sm font-medium text-zinc-700">
            Dirección
          </label>
          <input
            id="company-address"
            name="address"
            type="text"
            maxLength={300}
            value={address}
            onChange={(event) => setAddress(event.target.value)}
            disabled={isSubmitting}
            className={inputClassName}
            placeholder="Calle 123 # 45-67"
          />
        </div>

        <div className="space-y-2">
          <label htmlFor="company-phone" className="block text-sm font-medium text-zinc-700">
            Teléfono
          </label>
          <input
            id="company-phone"
            name="phone"
            type="tel"
            maxLength={30}
            value={phone}
            onChange={(event) => setPhone(event.target.value)}
            disabled={isSubmitting}
            className={inputClassName}
            placeholder="+57 300 123 4567"
          />
        </div>

        <div className="space-y-2">
          <label htmlFor="company-email" className="block text-sm font-medium text-zinc-700">
            Email
          </label>
          <input
            id="company-email"
            name="email"
            type="email"
            maxLength={255}
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            disabled={isSubmitting}
            className={inputClassName}
            placeholder="empresa@correo.com"
          />
        </div>
      </div>

      <div className="mt-6 border-t border-zinc-200 pt-6">
        <div className="flex flex-wrap justify-end gap-3">
          <button
            type="button"
            onClick={() => {
              setError(null);
              setSuccess(null);
            }}
            disabled={isSubmitting}
            className="inline-flex items-center justify-center rounded-lg border border-zinc-300 bg-white px-4 py-2 text-sm font-semibold text-zinc-700 shadow-sm transition-colors hover:border-zinc-400 hover:bg-zinc-50 disabled:cursor-not-allowed disabled:opacity-50"
          >
            Cancelar
          </button>
          <Button type="submit" disabled={isSubmitting}>
            {isSubmitting ? "Guardando..." : "Guardar Cambios"}
          </Button>
        </div>
      </div>

      {error ? (
        <div
          id="settings-form-error"
          role="alert"
          className="mt-4 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700"
        >
          {error}
        </div>
      ) : null}

      {success ? (
        <div
          role="status"
          className="mt-4 rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-700"
        >
          {success}
        </div>
      ) : null}
    </form>
  );
}
