"use client";

import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";

import { Button } from "@/components/ui/button";
import { ApiError, createEmployee } from "@/lib/api";

const inputClassName =
  "mt-1 block w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-950 shadow-sm outline-none transition focus:border-slate-900 focus:ring-2 focus:ring-slate-900/10 disabled:cursor-not-allowed disabled:bg-slate-50 disabled:text-slate-500";

const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const datePattern = /^\d{4}-\d{2}-\d{2}$/;
const salaryPattern = /^\d+(\.\d{1,2})?$/;

function isValidIsoDate(value: string): boolean {
  if (!datePattern.test(value)) {
    return false;
  }

  const timestamp = Date.parse(`${value}T00:00:00Z`);

  return (
    !Number.isNaN(timestamp) &&
    new Date(timestamp).toISOString().slice(0, 10) === value
  );
}

export function EmployeeForm() {
  const router = useRouter();
  const [document, setDocument] = useState("");
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [email, setEmail] = useState("");
  const [baseSalary, setBaseSalary] = useState("");
  const [startDate, setStartDate] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(
    event: FormEvent<HTMLFormElement>,
  ): Promise<void> {
    event.preventDefault();

    const trimmedDocument = document.trim();
    const trimmedFirstName = firstName.trim();
    const trimmedLastName = lastName.trim();
    const trimmedEmail = email.trim();
    const trimmedSalary = baseSalary.trim();
    const trimmedStartDate = startDate.trim();

    if (!trimmedDocument) {
      setError("El documento es obligatorio.");
      setSuccess(null);
      return;
    }

    if (!trimmedFirstName) {
      setError("El nombre es obligatorio.");
      setSuccess(null);
      return;
    }

    if (!trimmedLastName) {
      setError("El apellido es obligatorio.");
      setSuccess(null);
      return;
    }

    if (trimmedEmail && !emailPattern.test(trimmedEmail)) {
      setError("El correo electrónico no tiene un formato válido.");
      setSuccess(null);
      return;
    }

    if (!salaryPattern.test(trimmedSalary) || Number(trimmedSalary) <= 0) {
      setError("El salario base debe ser un número mayor que cero, con hasta 2 decimales.");
      setSuccess(null);
      return;
    }

    if (!isValidIsoDate(trimmedStartDate)) {
      setError("La fecha de inicio debe tener el formato YYYY-MM-DD y ser una fecha válida.");
      setSuccess(null);
      return;
    }

    setError(null);
    setSuccess(null);
    setIsSubmitting(true);

    try {
      await createEmployee({
        document: trimmedDocument,
        first_name: trimmedFirstName,
        last_name: trimmedLastName,
        ...(trimmedEmail ? { email: trimmedEmail } : {}),
        base_salary: trimmedSalary,
        start_date: trimmedStartDate,
      });

      setDocument("");
      setFirstName("");
      setLastName("");
      setEmail("");
      setBaseSalary("");
      setStartDate("");
      setSuccess("Empleado creado correctamente.");
      router.refresh();
    } catch (cause) {
      setError(
        cause instanceof ApiError
          ? `No se pudo crear el empleado: ${cause.message}`
          : "No se pudo crear el empleado. Revisa tu conexión e inténtalo de nuevo.",
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
            htmlFor="employee-document"
            className="block text-sm font-medium text-slate-700"
          >
            Documento{" "}
            <span className="text-red-600" aria-hidden="true">
              *
            </span>
          </label>
          <input
            id="employee-document"
            name="document"
            type="text"
            required
            maxLength={30}
            autoComplete="off"
            value={document}
            onChange={(event) => setDocument(event.target.value)}
            disabled={isSubmitting}
            className={`${inputClassName} font-mono`}
            placeholder="Ej. CC-1001"
          />
        </div>

        <div>
          <label
            htmlFor="employee-start-date"
            className="block text-sm font-medium text-slate-700"
          >
            Fecha de inicio{" "}
            <span className="text-red-600" aria-hidden="true">
              *
            </span>
          </label>
          <input
            id="employee-start-date"
            name="start_date"
            type="date"
            required
            value={startDate}
            onChange={(event) => setStartDate(event.target.value)}
            disabled={isSubmitting}
            className={inputClassName}
          />
          <p className="mt-1 text-xs text-slate-500">Formato: AAAA-MM-DD.</p>
        </div>

        <div>
          <label
            htmlFor="employee-first-name"
            className="block text-sm font-medium text-slate-700"
          >
            Nombre{" "}
            <span className="text-red-600" aria-hidden="true">
              *
            </span>
          </label>
          <input
            id="employee-first-name"
            name="first_name"
            type="text"
            required
            maxLength={100}
            autoComplete="given-name"
            value={firstName}
            onChange={(event) => setFirstName(event.target.value)}
            disabled={isSubmitting}
            className={inputClassName}
            placeholder="Ej. Ana"
          />
        </div>

        <div>
          <label
            htmlFor="employee-last-name"
            className="block text-sm font-medium text-slate-700"
          >
            Apellido{" "}
            <span className="text-red-600" aria-hidden="true">
              *
            </span>
          </label>
          <input
            id="employee-last-name"
            name="last_name"
            type="text"
            required
            maxLength={100}
            autoComplete="family-name"
            value={lastName}
            onChange={(event) => setLastName(event.target.value)}
            disabled={isSubmitting}
            className={inputClassName}
            placeholder="Ej. Pérez"
          />
        </div>

        <div>
          <label
            htmlFor="employee-email"
            className="block text-sm font-medium text-slate-700"
          >
            Email{" "}
            <span className="text-xs font-normal text-slate-400">
              (opcional)
            </span>
          </label>
          <input
            id="employee-email"
            name="email"
            type="email"
            maxLength={255}
            autoComplete="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            disabled={isSubmitting}
            className={inputClassName}
            placeholder="empleado@empresa.com"
          />
        </div>

        <div>
          <label
            htmlFor="employee-base-salary"
            className="block text-sm font-medium text-slate-700"
          >
            Salario base{" "}
            <span className="text-red-600" aria-hidden="true">
              *
            </span>
          </label>
          <input
            id="employee-base-salary"
            name="base_salary"
            type="number"
            required
            min="0.01"
            step="0.01"
            inputMode="decimal"
            value={baseSalary}
            onChange={(event) => setBaseSalary(event.target.value)}
            disabled={isSubmitting}
            className={inputClassName}
            placeholder="Ej. 2500000.00"
          />
        </div>
      </div>

      {error ? (
        <p
          id="employee-form-error"
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
          {isSubmitting ? "Creando..." : "Crear Empleado"}
        </Button>
      </div>
    </form>
  );
}
