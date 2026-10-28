"use client";

import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";

import { Button } from "@/components/ui/button";
import {
  ApiError,
  createBankAccount,
  type AccountingAccount,
  type BankAccountCreateInput,
  type BankAccountType,
} from "@/lib/api";

const inputClassName =
  "mt-1 block w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-950 shadow-sm outline-none transition focus:border-violet-500 focus:ring-2 focus:ring-violet-500/20 disabled:cursor-not-allowed disabled:bg-slate-50 disabled:text-slate-500";

const ACCOUNT_TYPES: { value: BankAccountType; label: string }[] = [
  { value: "CHECKING", label: "Cuenta corriente" },
  { value: "SAVINGS", label: "Cuenta de ahorros" },
];

interface BankAccountFormProps {
  pucAccounts: AccountingAccount[];
}

export function BankAccountForm({ pucAccounts }: BankAccountFormProps) {
  const router = useRouter();
  const defaultPucCode =
    pucAccounts.find((account) => account.code === "111005")?.code ??
    pucAccounts[0]?.code ??
    "111005";

  const [name, setName] = useState("");
  const [bankName, setBankName] = useState("");
  const [accountNumber, setAccountNumber] = useState("");
  const [accountType, setAccountType] =
    useState<BankAccountType>("CHECKING");
  const [accountingAccountCode, setAccountingAccountCode] =
    useState(defaultPucCode);
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(
    event: FormEvent<HTMLFormElement>,
  ): Promise<void> {
    event.preventDefault();

    const trimmedName = name.trim();
    const trimmedBankName = bankName.trim();
    const trimmedAccountNumber = accountNumber.trim();

    if (!trimmedName || !trimmedBankName || !trimmedAccountNumber) {
      setError("Nombre, banco y número de cuenta son obligatorios.");
      return;
    }

    setError(null);
    setIsSubmitting(true);

    try {
      const payload: BankAccountCreateInput = {
        name: trimmedName,
        bank_name: trimmedBankName,
        account_number: trimmedAccountNumber,
        account_type: accountType,
        currency: "COP",
        accounting_account_code: accountingAccountCode,
      };
      const account = await createBankAccount(payload);
      router.push(`/treasury/accounts/${account.id}`);
      router.refresh();
    } catch (cause) {
      setError(
        cause instanceof ApiError
          ? `No se pudo crear la cuenta: ${cause.message}`
          : "No se pudo crear la cuenta. Revisa tu conexión e inténtalo de nuevo.",
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
            htmlFor="bank-account-name"
            className="block text-sm font-medium text-slate-700"
          >
            Nombre de la cuenta{" "}
            <span className="text-red-600" aria-hidden="true">
              *
            </span>
          </label>
          <input
            id="bank-account-name"
            name="name"
            type="text"
            required
            maxLength={100}
            autoComplete="off"
            value={name}
            onChange={(event) => setName(event.target.value)}
            disabled={isSubmitting}
            className={inputClassName}
            placeholder="Ej. Cuenta recaudadora"
          />
        </div>

        <div>
          <label
            htmlFor="bank-account-bank"
            className="block text-sm font-medium text-slate-700"
          >
            Banco{" "}
            <span className="text-red-600" aria-hidden="true">
              *
            </span>
          </label>
          <input
            id="bank-account-bank"
            name="bank_name"
            type="text"
            required
            maxLength={100}
            autoComplete="off"
            value={bankName}
            onChange={(event) => setBankName(event.target.value)}
            disabled={isSubmitting}
            className={inputClassName}
            placeholder="Ej. Bancolombia"
          />
        </div>

        <div>
          <label
            htmlFor="bank-account-number"
            className="block text-sm font-medium text-slate-700"
          >
            Número de cuenta{" "}
            <span className="text-red-600" aria-hidden="true">
              *
            </span>
          </label>
          <input
            id="bank-account-number"
            name="account_number"
            type="text"
            required
            maxLength={50}
            autoComplete="off"
            value={accountNumber}
            onChange={(event) => setAccountNumber(event.target.value)}
            disabled={isSubmitting}
            className={inputClassName}
            placeholder="Ej. 123456789"
          />
        </div>

        <div>
          <label
            htmlFor="bank-account-type"
            className="block text-sm font-medium text-slate-700"
          >
            Tipo de cuenta{" "}
            <span className="text-red-600" aria-hidden="true">
              *
            </span>
          </label>
          <select
            id="bank-account-type"
            name="account_type"
            value={accountType}
            onChange={(event) =>
              setAccountType(event.target.value as BankAccountType)
            }
            disabled={isSubmitting}
            className={inputClassName}
          >
            {ACCOUNT_TYPES.map((type) => (
              <option key={type.value} value={type.value}>
                {type.label}
              </option>
            ))}
          </select>
        </div>

        <div className="sm:col-span-2">
          <label
            htmlFor="bank-account-puc"
            className="block text-sm font-medium text-slate-700"
          >
            Cuenta PUC{" "}
            <span className="text-red-600" aria-hidden="true">
              *
            </span>
          </label>
          <select
            id="bank-account-puc"
            name="accounting_account_code"
            value={accountingAccountCode}
            onChange={(event) => setAccountingAccountCode(event.target.value)}
            disabled={isSubmitting}
            className={inputClassName}
          >
            {pucAccounts.map((account) => (
              <option key={account.code} value={account.code}>
                {account.code} · {account.name}
              </option>
            ))}
          </select>
          <p className="mt-1 text-xs text-slate-500">
            Cada cuenta bancaria debe apuntar a una cuenta auxiliar del grupo
            11. Usa cuentas distintas para poder registrar transferencias entre
            bancos.
          </p>
        </div>
      </div>

      {error ? (
        <p
          role="alert"
          className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700"
        >
          {error}
        </p>
      ) : null}

      <div className="flex justify-end">
        <Button
          type="submit"
          disabled={isSubmitting}
          className="w-full sm:w-auto"
        >
          {isSubmitting ? "Creando cuenta..." : "Crear cuenta bancaria"}
        </Button>
      </div>
    </form>
  );
}
