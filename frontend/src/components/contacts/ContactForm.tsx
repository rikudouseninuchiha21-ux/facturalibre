"use client";

import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";

import { Button } from "@/components/ui/button";
import {
  ApiError,
  createContact,
  updateContact,
  type Contact,
} from "@/lib/api";

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

const PERSON_TYPES: { value: string; label: string }[] = [
  { value: "NATURAL", label: "Persona natural" },
  { value: "JURIDICA", label: "Persona jurídica" },
];

const TAX_REGIMES: { value: string; label: string }[] = [
  { value: "RESPONSABLE_IVA", label: "Responsable de IVA" },
  { value: "NO_RESPONSABLE", label: "No responsable de IVA" },
  { value: "GRAN_CONTRIBUYENTE", label: "Gran contribuyente" },
  { value: "AUTORRETENEDOR", label: "Autorretenedor" },
  { value: "REGIMEN_SIMPLE", label: "Régimen simple de tributación" },
];

const FISCAL_RESPONSIBILITIES: { value: string; label: string }[] = [
  { value: "O-13", label: "O-13 · Gran contribuyente" },
  { value: "O-15", label: "O-15 · Autorretenedor" },
  { value: "O-23", label: "O-23 · Agente retención IVA" },
  { value: "O-47", label: "O-47 · Régimen simple" },
  { value: "R-99-PN", label: "R-99-PN · No responsable" },
];

interface ContactFormProps {
  /** Contacto a editar; sin él, el formulario crea uno nuevo. */
  contact?: Contact;
  onSaved?: () => void;
  onCancel?: () => void;
}

export function ContactForm({ contact, onSaved, onCancel }: ContactFormProps) {
  const router = useRouter();
  const isEditing = contact !== undefined;

  const [name, setName] = useState(contact?.name ?? "");
  const [email, setEmail] = useState(contact?.email ?? "");
  const [taxId, setTaxId] = useState(contact?.tax_id ?? "");
  const [type, setType] = useState<"customer" | "supplier" | "both">(
    (contact?.type as "customer" | "supplier" | "both") ?? "customer",
  );
  const [status, setStatus] = useState<"LEAD" | "PROSPECT" | "CUSTOMER">(
    (contact?.status as "LEAD" | "PROSPECT" | "CUSTOMER") ?? "CUSTOMER",
  );

  // Datos fiscales DIAN (Fase 38A).
  const [address, setAddress] = useState(contact?.address ?? "");
  const [dv, setDv] = useState(contact?.dv ?? "");
  const [personType, setPersonType] = useState(contact?.person_type ?? "");
  const [taxRegime, setTaxRegime] = useState(contact?.tax_regime ?? "");
  const [fiscalResponsibility, setFiscalResponsibility] = useState(
    contact?.fiscal_responsibility ?? "",
  );
  const [municipalityCode, setMunicipalityCode] = useState(
    contact?.dian_municipality_code ?? "",
  );
  const [departmentCode, setDepartmentCode] = useState(
    contact?.dian_department_code ?? "",
  );

  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(
    event: FormEvent<HTMLFormElement>,
  ): Promise<void> {
    event.preventDefault();

    const trimmedName = name.trim();
    const trimmedDv = dv.trim();
    const trimmedMunicipality = municipalityCode.trim();
    const trimmedDepartment = departmentCode.trim();

    if (!trimmedName) {
      setError("El nombre es obligatorio.");
      setSuccess(null);
      return;
    }
    if (trimmedDv && !/^\d{1,2}$/.test(trimmedDv)) {
      setError("El dígito de verificación (DV) debe ser 1 o 2 dígitos.");
      setSuccess(null);
      return;
    }
    if (trimmedMunicipality && !/^\d{5}$/.test(trimmedMunicipality)) {
      setError(
        "El código DANE del municipio debe tener 5 dígitos (ej. 11001).",
      );
      setSuccess(null);
      return;
    }
    if (trimmedDepartment && !/^\d{2}$/.test(trimmedDepartment)) {
      setError("El código DANE del departamento debe tener 2 dígitos (ej. 11).");
      setSuccess(null);
      return;
    }

    setError(null);
    setSuccess(null);
    setIsSubmitting(true);

    const sharedPayload = {
      name: trimmedName,
      type,
      status,
      ...(email.trim() ? { email: email.trim() } : {}),
      ...(taxId.trim() ? { tax_id: taxId.trim() } : {}),
      ...(address.trim() ? { address: address.trim() } : {}),
      ...(trimmedDv ? { dv: trimmedDv } : {}),
      ...(taxRegime ? { tax_regime: taxRegime } : {}),
      ...(personType ? { person_type: personType } : {}),
      ...(fiscalResponsibility ? { fiscal_responsibility: fiscalResponsibility } : {}),
      ...(trimmedMunicipality ? { dian_municipality_code: trimmedMunicipality } : {}),
      ...(trimmedDepartment ? { dian_department_code: trimmedDepartment } : {}),
    };

    try {
      if (isEditing && contact) {
        await updateContact(contact.id, {
          ...sharedPayload,
          version: contact.version,
        });
        setSuccess("Contacto actualizado correctamente.");
      } else {
        await createContact(sharedPayload);
        setName("");
        setEmail("");
        setTaxId("");
        setType("customer");
        setStatus("CUSTOMER");
        setAddress("");
        setDv("");
        setPersonType("");
        setTaxRegime("");
        setFiscalResponsibility("");
        setMunicipalityCode("");
        setDepartmentCode("");
        setSuccess("Contacto creado correctamente.");
      }
      router.refresh();
      onSaved?.();
    } catch (cause) {
      const fallback = isEditing
        ? "No se pudo actualizar el contacto."
        : "No se pudo crear el contacto.";
      setError(
        cause instanceof ApiError
          ? `${fallback} ${cause.message}`
          : `${fallback} Revisa tu conexión e inténtalo de nuevo.`,
      );
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} noValidate className="space-y-5">
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
            Tipo
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
              (sin dígito de verificación)
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

        <div className="sm:col-span-2">
          <label
            htmlFor="contact-address"
            className="block text-sm font-medium text-slate-700"
          >
            Dirección{" "}
            <span className="text-xs font-normal text-slate-400">
              (opcional)
            </span>
          </label>
          <input
            id="contact-address"
            name="address"
            type="text"
            maxLength={300}
            autoComplete="street-address"
            value={address}
            onChange={(event) => setAddress(event.target.value)}
            disabled={isSubmitting}
            className={inputClassName}
            placeholder="Calle 100 # 8-50"
          />
        </div>
      </div>

      {/* Datos fiscales DIAN (Fase 38A) */}
      <div className="border-t border-slate-200 pt-5">
        <h3 className="text-sm font-bold uppercase tracking-wider text-amber-700">
          Datos fiscales DIAN
        </h3>
        <p className="mt-1 text-sm text-slate-500">
          El generador de factura electrónica (XML UBL 2.1) los exige para
          emitir el documento. Puedes completarlos más tarde desde “Editar”.
        </p>
        <div className="mt-4 grid gap-4 sm:grid-cols-2">
          <div>
            <label
              htmlFor="contact-dv"
              className="block text-sm font-medium text-slate-700"
            >
              Dígito de verificación (DV)
            </label>
            <input
              id="contact-dv"
              name="dv"
              type="text"
              inputMode="numeric"
              maxLength={2}
              autoComplete="off"
              value={dv}
              onChange={(event) => setDv(event.target.value)}
              disabled={isSubmitting}
              className={inputClassName}
              placeholder="Ej. 8"
            />
          </div>

          <div>
            <label
              htmlFor="contact-person-type"
              className="block text-sm font-medium text-slate-700"
            >
              Tipo de persona
            </label>
            <select
              id="contact-person-type"
              name="person_type"
              value={personType}
              onChange={(event) => setPersonType(event.target.value)}
              disabled={isSubmitting}
              className={inputClassName}
            >
              <option value="">Sin definir</option>
              {PERSON_TYPES.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label
              htmlFor="contact-tax-regime"
              className="block text-sm font-medium text-slate-700"
            >
              Régimen tributario
            </label>
            <select
              id="contact-tax-regime"
              name="tax_regime"
              value={taxRegime}
              onChange={(event) => setTaxRegime(event.target.value)}
              disabled={isSubmitting}
              className={inputClassName}
            >
              <option value="">Sin definir</option>
              {TAX_REGIMES.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label
              htmlFor="contact-fiscal-responsibility"
              className="block text-sm font-medium text-slate-700"
            >
              Responsabilidad fiscal
            </label>
            <select
              id="contact-fiscal-responsibility"
              name="fiscal_responsibility"
              value={fiscalResponsibility}
              onChange={(event) => setFiscalResponsibility(event.target.value)}
              disabled={isSubmitting}
              className={inputClassName}
            >
              <option value="">Sin definir</option>
              {FISCAL_RESPONSIBILITIES.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label
              htmlFor="contact-municipality"
              className="block text-sm font-medium text-slate-700"
            >
              Código DANE municipio{" "}
              <span className="text-xs font-normal text-slate-400">
                (ej. 11001)
              </span>
            </label>
            <input
              id="contact-municipality"
              name="dian_municipality_code"
              type="text"
              inputMode="numeric"
              maxLength={5}
              autoComplete="off"
              value={municipalityCode}
              onChange={(event) => setMunicipalityCode(event.target.value)}
              disabled={isSubmitting}
              className={inputClassName}
              placeholder="11001"
            />
          </div>

          <div>
            <label
              htmlFor="contact-department"
              className="block text-sm font-medium text-slate-700"
            >
              Código DANE departamento{" "}
              <span className="text-xs font-normal text-slate-400">
                (ej. 11)
              </span>
            </label>
            <input
              id="contact-department"
              name="dian_department_code"
              type="text"
              inputMode="numeric"
              maxLength={2}
              autoComplete="off"
              value={departmentCode}
              onChange={(event) => setDepartmentCode(event.target.value)}
              disabled={isSubmitting}
              className={inputClassName}
              placeholder="11"
            />
          </div>
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

      <div className="flex flex-wrap justify-end gap-2">
        {onCancel ? (
          <Button
            type="button"
            onClick={onCancel}
            disabled={isSubmitting}
            className="border border-slate-300 bg-white text-slate-700 hover:bg-slate-50"
          >
            Cancelar
          </Button>
        ) : null}
        <Button type="submit" disabled={isSubmitting} className="w-full sm:w-auto">
          {isSubmitting
            ? isEditing
              ? "Guardando..."
              : "Creando..."
            : isEditing
              ? "Guardar Cambios"
              : "Crear Contacto"}
        </Button>
      </div>
    </form>
  );
}
