"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import {
  ApiError,
  registerInitialCapital,
  type BankAccount,
  type InitialCapitalEntry,
} from "@/lib/api";

const inputClassName =
  "mt-1 block w-full rounded-lg border border-zinc-300 bg-white px-3 py-2 text-sm text-zinc-950 shadow-sm outline-none transition focus:border-violet-600 focus:ring-2 focus:ring-violet-500/10 disabled:cursor-not-allowed disabled:bg-zinc-50 disabled:text-zinc-500";

interface InitialCapitalFormProps {
  bankAccounts: BankAccount[];
  initialDate: string;
}

export function InitialCapitalForm({
  bankAccounts,
  initialDate,
}: InitialCapitalFormProps) {
  const router = useRouter();
  const [amount, setAmount] = useState("");
  const [entryDate, setEntryDate] = useState(initialDate);
  const [bankAccountId, setBankAccountId] = useState("");
  const [description, setDescription] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [created, setCreated] = useState<InitialCapitalEntry | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(
    event: React.FormEvent<HTMLFormElement>,
  ): Promise<void> {
    event.preventDefault();

    setError(null);
    setCreated(null);
    setIsSubmitting(true);

    try {
      const entry = await registerInitialCapital({
        amount: amount.trim(),
        entry_date: entryDate || undefined,
        bank_account_id: bankAccountId || undefined,
        description: description.trim() || undefined,
      });
      setCreated(entry);
      setAmount("");
      setDescription("");
      setTimeout(() => router.refresh(), 2000);
    } catch (cause) {
      setError(
        cause instanceof ApiError
          ? cause.message
          : "No se pudo registrar el capital inicial. Inténtalo de nuevo.",
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
            htmlFor="capital-amount"
            className="block text-sm font-medium text-zinc-700"
          >
            Monto del aporte{" "}
            <span className="text-red-600" aria-hidden="true">
              *
            </span>
          </label>
          <input
            id="capital-amount"
            name="amount"
            type="number"
            step="0.01"
            min="0.01"
            required
            value={amount}
            onChange={(event) => setAmount(event.target.value)}
            disabled={isSubmitting}
            className={inputClassName}
            placeholder="50000000.00"
          />
        </div>

        <div className="space-y-2">
          <label
            htmlFor="capital-date"
            className="block text-sm font-medium text-zinc-700"
          >
            Fecha del asiento
          </label>
          <input
            id="capital-date"
            name="entry_date"
            type="date"
            value={entryDate}
            onChange={(event) => setEntryDate(event.target.value)}
            disabled={isSubmitting}
            className={inputClassName}
          />
        </div>

        <div className="space-y-2">
          <label
            htmlFor="capital-bank"
            className="block text-sm font-medium text-zinc-700"
          >
            Cuenta de destino
          </label>
          <select
            id="capital-bank"
            name="bank_account_id"
            value={bankAccountId}
            onChange={(event) => setBankAccountId(event.target.value)}
            disabled={isSubmitting}
            className={inputClassName}
          >
            <option value="">Bancos (111005) — cuenta genérica</option>
            {bankAccounts.map((account) => (
              <option key={account.id} value={account.id}>
                {account.name} — {account.bank_name} ({account.account_number})
              </option>
            ))}
          </select>
        </div>

        <div className="space-y-2">
          <label
            htmlFor="capital-description"
            className="block text-sm font-medium text-zinc-700"
          >
            Descripción
          </label>
          <input
            id="capital-description"
            name="description"
            type="text"
            maxLength={500}
            value={description}
            onChange={(event) => setDescription(event.target.value)}
            disabled={isSubmitting}
            className={inputClassName}
            placeholder="Aporte de capital inicial de los socios"
          />
        </div>
      </div>

      <p className="text-xs text-zinc-500">
        Genera el asiento contable Débito a la cuenta bancaria seleccionada (o a
        Bancos 111005) y Crédito a Capital suscrito y pagado (3105). Se permite
        registrar aportes sucesivos.
      </p>

      <div className="border-t border-zinc-200 pt-6">
        <div className="flex flex-wrap justify-end gap-3">
          <Button type="submit" disabled={isSubmitting}>
            {isSubmitting ? "Registrando..." : "Registrar Capital"}
          </Button>
        </div>
      </div>

      {error ? (
        <div
          id="capital-form-error"
          role="alert"
          className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700"
        >
          {error}
        </div>
      ) : null}

      {created ? (
        <div
          role="status"
          className="space-y-2 rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-700"
        >
          <p className="font-semibold">
            Capital registrado correctamente (asiento {created.id.slice(0, 8)}).
          </p>
          <ul className="list-disc pl-5">
            {created.lines.map((line) => (
              <li key={line.id}>
                {line.account_code} {line.account_name}:{" "}
                {Number(line.debit) > 0
                  ? `débito $${Number(line.debit).toLocaleString("es-CO")}`
                  : `crédito $${Number(line.credit).toLocaleString("es-CO")}`}
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </form>
  );
}
