"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { ApiError, updateCompanySettings, type CompanySetting } from "@/lib/api";

const inputClassName =
  "mt-1 block w-full rounded-lg border border-zinc-300 bg-white px-3 py-2 text-sm text-zinc-950 shadow-sm outline-none transition focus:border-violet-600 focus:ring-2 focus:ring-violet-500/10 disabled:cursor-not-allowed disabled:bg-zinc-50 disabled:text-zinc-500";

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
  const [dv, setDv] = useState(companySettings.dv ?? "");
  const [taxRegime, setTaxRegime] = useState(companySettings.tax_regime ?? "");
  const [personType, setPersonType] = useState(
    companySettings.person_type ?? "",
  );
  const [fiscalResponsibility, setFiscalResponsibility] = useState(
    companySettings.fiscal_responsibility ?? "",
  );
  const [municipalityCode, setMunicipalityCode] = useState(
    companySettings.dian_municipality_code ?? "",
  );
  const [departmentCode, setDepartmentCode] = useState(
    companySettings.dian_department_code ?? "",
  );
  const [resolutionNumber, setResolutionNumber] = useState(
    companySettings.dian_resolution_number ?? "",
  );
  const [resolutionPrefix, setResolutionPrefix] = useState(
    companySettings.dian_resolution_prefix ?? "",
  );
  const [rangeFrom, setRangeFrom] = useState(
    companySettings.dian_resolution_range_from?.toString() ?? "",
  );
  const [rangeTo, setRangeTo] = useState(
    companySettings.dian_resolution_range_to?.toString() ?? "",
  );
  const [validFrom, setValidFrom] = useState(
    companySettings.dian_resolution_valid_from ?? "",
  );
  const [validTo, setValidTo] = useState(
    companySettings.dian_resolution_valid_to ?? "",
  );
  const [softwareId, setSoftwareId] = useState(
    companySettings.dian_software_id ?? "",
  );
  const [softwarePin, setSoftwarePin] = useState(
    companySettings.dian_software_pin ?? "",
  );
  const [environment, setEnvironment] = useState(
    companySettings.dian_environment ?? "HABILITACION",
  );
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
        dv: dv.trim() || undefined,
        tax_regime: taxRegime.trim() || undefined,
        person_type: personType.trim() || undefined,
        fiscal_responsibility: fiscalResponsibility.trim() || undefined,
        dian_municipality_code: municipalityCode.trim() || undefined,
        dian_department_code: departmentCode.trim() || undefined,
        dian_resolution_number: resolutionNumber.trim() || undefined,
        dian_resolution_prefix: resolutionPrefix.trim() || undefined,
        dian_resolution_range_from: rangeFrom.trim()
          ? Number(rangeFrom.trim())
          : undefined,
        dian_resolution_range_to: rangeTo.trim()
          ? Number(rangeTo.trim())
          : undefined,
        dian_resolution_valid_from: validFrom || undefined,
        dian_resolution_valid_to: validTo || undefined,
        dian_software_id: softwareId.trim() || undefined,
        dian_software_pin: softwarePin.trim() || undefined,
        dian_environment: environment,
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

      {/* Datos DIAN de la empresa (Fase 38A) */}
      <div className="mt-6 border-t border-zinc-200 pt-6">
        <h3 className="text-sm font-bold uppercase tracking-wider text-violet-700">
          Facturación electrónica DIAN
        </h3>
        <p className="mt-1 text-sm text-zinc-500">
          Datos del emisor para el XML UBL 2.1 y el PDF con QR. El NIT es el
          campo “NIT / Tax ID”.
        </p>
        <div className="mt-4 grid gap-6 md:grid-cols-3">
          <div className="space-y-2">
            <label htmlFor="company-dv" className="block text-sm font-medium text-zinc-700">
              Dígito de verificación (DV)
            </label>
            <input
              id="company-dv"
              type="text"
              maxLength={2}
              value={dv}
              onChange={(event) => setDv(event.target.value)}
              disabled={isSubmitting}
              className={inputClassName}
              placeholder="8"
            />
          </div>
          <div className="space-y-2">
            <label htmlFor="company-person-type" className="block text-sm font-medium text-zinc-700">
              Tipo de persona
            </label>
            <select
              id="company-person-type"
              value={personType}
              onChange={(event) => setPersonType(event.target.value)}
              disabled={isSubmitting}
              className={inputClassName}
            >
              <option value="">Sin definir</option>
              <option value="NATURAL">Natural</option>
              <option value="JURIDICA">Jurídica</option>
            </select>
          </div>
          <div className="space-y-2">
            <label htmlFor="company-tax-regime" className="block text-sm font-medium text-zinc-700">
              Régimen tributario
            </label>
            <select
              id="company-tax-regime"
              value={taxRegime}
              onChange={(event) => setTaxRegime(event.target.value)}
              disabled={isSubmitting}
              className={inputClassName}
            >
              <option value="">Sin definir</option>
              <option value="RESPONSABLE_IVA">Responsable de IVA</option>
              <option value="NO_RESPONSABLE">No responsable</option>
              <option value="GRAN_CONTRIBUYENTE">Gran contribuyente</option>
              <option value="AUTORRETENEDOR">Autorretenedor</option>
              <option value="REGIMEN_SIMPLE">Régimen simple</option>
            </select>
          </div>
          <div className="space-y-2">
            <label htmlFor="company-fiscal-responsibility" className="block text-sm font-medium text-zinc-700">
              Responsabilidad fiscal
            </label>
            <select
              id="company-fiscal-responsibility"
              value={fiscalResponsibility}
              onChange={(event) => setFiscalResponsibility(event.target.value)}
              disabled={isSubmitting}
              className={inputClassName}
            >
              <option value="">Sin definir</option>
              <option value="O-13">O-13 · Gran contribuyente</option>
              <option value="O-15">O-15 · Autorretenedor</option>
              <option value="O-23">O-23 · Agente retención IVA</option>
              <option value="O-47">O-47 · Régimen simple</option>
              <option value="R-99-PN">R-99-PN · No responsable</option>
            </select>
          </div>
          <div className="space-y-2">
            <label htmlFor="company-municipality" className="block text-sm font-medium text-zinc-700">
              Código DANE municipio
            </label>
            <input
              id="company-municipality"
              type="text"
              maxLength={5}
              value={municipalityCode}
              onChange={(event) => setMunicipalityCode(event.target.value)}
              disabled={isSubmitting}
              className={inputClassName}
              placeholder="11001"
            />
          </div>
          <div className="space-y-2">
            <label htmlFor="company-department" className="block text-sm font-medium text-zinc-700">
              Código DANE departamento
            </label>
            <input
              id="company-department"
              type="text"
              maxLength={2}
              value={departmentCode}
              onChange={(event) => setDepartmentCode(event.target.value)}
              disabled={isSubmitting}
              className={inputClassName}
              placeholder="11"
            />
          </div>
        </div>

        <h4 className="mt-6 text-sm font-semibold text-zinc-800">
          Resolución de facturación
        </h4>
        <div className="mt-3 grid gap-6 md:grid-cols-3">
          <div className="space-y-2">
            <label htmlFor="company-resolution-number" className="block text-sm font-medium text-zinc-700">
              Número de resolución
            </label>
            <input
              id="company-resolution-number"
              type="text"
              maxLength={20}
              value={resolutionNumber}
              onChange={(event) => setResolutionNumber(event.target.value)}
              disabled={isSubmitting}
              className={inputClassName}
              placeholder="18764000123456"
            />
          </div>
          <div className="space-y-2">
            <label htmlFor="company-resolution-prefix" className="block text-sm font-medium text-zinc-700">
              Prefijo autorizado
            </label>
            <input
              id="company-resolution-prefix"
              type="text"
              maxLength={4}
              value={resolutionPrefix}
              onChange={(event) => setResolutionPrefix(event.target.value)}
              disabled={isSubmitting}
              className={inputClassName}
              placeholder="FE"
            />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-2">
              <label htmlFor="company-range-from" className="block text-sm font-medium text-zinc-700">
                Rango desde
              </label>
              <input
                id="company-range-from"
                type="number"
                min={1}
                value={rangeFrom}
                onChange={(event) => setRangeFrom(event.target.value)}
                disabled={isSubmitting}
                className={inputClassName}
              />
            </div>
            <div className="space-y-2">
              <label htmlFor="company-range-to" className="block text-sm font-medium text-zinc-700">
                Rango hasta
              </label>
              <input
                id="company-range-to"
                type="number"
                min={1}
                value={rangeTo}
                onChange={(event) => setRangeTo(event.target.value)}
                disabled={isSubmitting}
                className={inputClassName}
              />
            </div>
          </div>
          <div className="space-y-2">
            <label htmlFor="company-valid-from" className="block text-sm font-medium text-zinc-700">
              Vigencia desde
            </label>
            <input
              id="company-valid-from"
              type="date"
              value={validFrom}
              onChange={(event) => setValidFrom(event.target.value)}
              disabled={isSubmitting}
              className={inputClassName}
            />
          </div>
          <div className="space-y-2">
            <label htmlFor="company-valid-to" className="block text-sm font-medium text-zinc-700">
              Vigencia hasta
            </label>
            <input
              id="company-valid-to"
              type="date"
              value={validTo}
              onChange={(event) => setValidTo(event.target.value)}
              disabled={isSubmitting}
              className={inputClassName}
            />
          </div>
        </div>

        <h4 className="mt-6 text-sm font-semibold text-zinc-800">
          Software proveedor y ambiente
        </h4>
        <div className="mt-3 grid gap-6 md:grid-cols-3">
          <div className="space-y-2">
            <label htmlFor="company-software-id" className="block text-sm font-medium text-zinc-700">
              Identificación del software
            </label>
            <input
              id="company-software-id"
              type="text"
              maxLength={100}
              value={softwareId}
              onChange={(event) => setSoftwareId(event.target.value)}
              disabled={isSubmitting}
              className={inputClassName}
              placeholder="VANTAGE-ERP"
            />
          </div>
          <div className="space-y-2">
            <label htmlFor="company-software-pin" className="block text-sm font-medium text-zinc-700">
              PIN del software (ClTec)
            </label>
            <input
              id="company-software-pin"
              type="password"
              maxLength={100}
              value={softwarePin}
              onChange={(event) => setSoftwarePin(event.target.value)}
              disabled={isSubmitting}
              className={inputClassName}
              placeholder="Sin PIN → CUFE de prueba"
            />
          </div>
          <div className="space-y-2">
            <label htmlFor="company-environment" className="block text-sm font-medium text-zinc-700">
              Ambiente
            </label>
            <select
              id="company-environment"
              value={environment}
              onChange={(event) => setEnvironment(
                event.target.value as "HABILITACION" | "PRODUCCION",
              )}
              disabled={isSubmitting}
              className={inputClassName}
            >
              <option value="HABILITACION">Habilitación</option>
              <option value="PRODUCCION">Producción</option>
            </select>
          </div>
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
