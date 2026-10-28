import type { Metadata } from "next";
import Link from "next/link";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { BankAccountForm } from "@/components/treasury/BankAccountForm";
import { getTreasuryPucAccounts, type AccountingAccount } from "@/lib/api";
import { getSessionCookieHeader } from "@/lib/server-auth";

export const dynamic = "force-dynamic";

export const metadata: Metadata = {
  title: "Nueva cuenta bancaria",
};

export default async function NewBankAccountPage() {
  const cookieHeader = await getSessionCookieHeader();

  let pucAccounts: AccountingAccount[] = [];
  let error: string | null = null;

  try {
    const accounts = await getTreasuryPucAccounts(cookieHeader);
    pucAccounts = accounts.filter((account) =>
      account.code.startsWith("11"),
    );
  } catch (cause) {
    error =
      cause instanceof Error
        ? cause.message
        : "No se pudo consultar el catálogo PUC.";
  }

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <header>
        <Link
          href="/treasury"
          className="text-sm font-medium text-violet-600 transition-colors hover:text-violet-800"
        >
          ← Volver a tesorería
        </Link>
        <h1 className="mt-2 text-3xl font-bold tracking-tight text-slate-950">
          Nueva cuenta bancaria
        </h1>
        <p className="mt-2 max-w-2xl text-slate-600">
          Registra la cuenta y asígnala a una cuenta auxiliar del PUC del grupo
          11 (Disponible). El saldo inicial se registra con un depósito.
        </p>
      </header>

      <Card>
        <CardHeader>
          <CardTitle>Datos de la cuenta</CardTitle>
        </CardHeader>
        <CardContent>
          {error ? (
            <div
              role="alert"
              className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700"
            >
              {error}
            </div>
          ) : pucAccounts.length === 0 ? (
            <div className="rounded-xl border border-violet-200 bg-violet-50 px-4 py-3 text-sm text-violet-700">
              No hay cuentas PUC del grupo 11 disponibles. Revisa la
              configuración contable antes de crear una cuenta bancaria.
            </div>
          ) : (
            <BankAccountForm pucAccounts={pucAccounts} />
          )}
        </CardContent>
      </Card>
    </div>
  );
}
