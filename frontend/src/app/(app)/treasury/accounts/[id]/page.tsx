import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";

import { TreasuryAccountDetail } from "@/components/treasury/TreasuryAccountDetail";
import {
  ApiError,
  getBankAccount,
  getBankAccounts,
  getBankTransactions,
  getTreasuryPucAccounts,
  type AccountingAccount,
  type BankAccount,
  type BankTransaction,
} from "@/lib/api";
import { getSessionCookieHeader } from "@/lib/server-auth";

export const dynamic = "force-dynamic";

export async function generateMetadata({
  params,
}: {
  params: Promise<{ id: string }>;
}): Promise<Metadata> {
  const { id } = await params;
  return {
    title: `Cuenta bancaria ${id}`,
  };
}

export default async function BankAccountPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const cookieHeader = await getSessionCookieHeader();

  let account: BankAccount | null = null;
  let accounts: BankAccount[] = [];
  let transactions: BankTransaction[] = [];
  let pucAccounts: AccountingAccount[] = [];
  let error: string | null = null;

  try {
    [account, accounts, transactions, pucAccounts] = await Promise.all([
      getBankAccount(id, cookieHeader),
      getBankAccounts(cookieHeader),
      getBankTransactions(id, cookieHeader),
      getTreasuryPucAccounts(cookieHeader),
    ]);
  } catch (cause) {
    if (cause instanceof ApiError && cause.status === 404) {
      notFound();
    }
    error =
      cause instanceof Error
        ? cause.message
        : "No se pudo cargar la cuenta bancaria.";
  }

  if (!account) {
    return (
      <div className="mx-auto max-w-4xl py-10">
        <div
          role="alert"
          className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700"
        >
          {error ?? "Cuenta bancaria no encontrada."}
        </div>
        <div className="mt-6">
          <Link
            href="/treasury"
            className="text-sm font-medium text-amber-600 hover:text-amber-800"
          >
            ← Volver a tesorería
          </Link>
        </div>
      </div>
    );
  }

  const today = new Date().toISOString().slice(0, 10);

  return (
    <div className="space-y-6">
      <header>
        <Link
          href="/treasury"
          className="text-sm font-medium text-amber-600 transition-colors hover:text-amber-800"
        >
          ← Volver a tesorería
        </Link>
        <div className="mt-2 flex flex-wrap items-start justify-between gap-4">
          <div>
            <h1 className="text-3xl font-bold tracking-tight text-slate-950">
              {account.name}
            </h1>
            <p className="mt-2 text-slate-600">
              {account.bank_name} · {account.account_number} ·{" "}
              {account.accounting_account_code}
            </p>
          </div>
          <span
            className={`inline-flex items-center rounded-full px-3 py-1 text-xs font-semibold ring-1 ring-inset ${
              account.is_active
                ? "bg-emerald-50 text-emerald-700 ring-emerald-200"
                : "bg-slate-100 text-slate-600 ring-slate-200"
            }`}
          >
            {account.is_active ? "Cuenta activa" : "Cuenta inactiva"}
          </span>
        </div>
      </header>

      <TreasuryAccountDetail
        account={account}
        accounts={accounts}
        transactions={transactions}
        pucAccounts={pucAccounts}
        today={today}
      />
    </div>
  );
}
