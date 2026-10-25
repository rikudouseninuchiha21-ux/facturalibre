import type { Metadata } from "next";
import Link from "next/link";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  getBankAccounts,
  getTreasurySummary,
  type BankAccount,
  type TreasurySummary,
} from "@/lib/api";
import { formatCurrency } from "@/lib/format";
import { getSessionCookieHeader } from "@/lib/server-auth";

export const dynamic = "force-dynamic";

export const metadata: Metadata = {
  title: "Tesorería",
};

const accountTypeLabels: Record<string, string> = {
  CHECKING: "Corriente",
  SAVINGS: "Ahorros",
};

export default async function TreasuryPage() {
  const cookieHeader = await getSessionCookieHeader();

  let accounts: BankAccount[] = [];
  let summary: TreasurySummary | null = null;
  let error: string | null = null;

  try {
    [accounts, summary] = await Promise.all([
      getBankAccounts(cookieHeader),
      getTreasurySummary(cookieHeader),
    ]);
  } catch (cause) {
    error =
      cause instanceof Error
        ? cause.message
        : "No se pudo consultar la información de tesorería.";
  }

  return (
    <div className="space-y-6">
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-slate-950">
            Tesorería
          </h1>
          <p className="mt-2 max-w-2xl text-slate-600">
            Cuentas bancarias, movimientos y conciliación. Cada movimiento
            genera su asiento contable automático.
          </p>
        </div>
        <Link
          href="/treasury/accounts/new"
          className="inline-flex items-center justify-center gap-2 rounded-lg bg-amber-600 px-4 py-2 text-sm font-semibold text-white shadow-sm transition-colors hover:bg-amber-700 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-amber-600"
        >
          <span aria-hidden="true">+</span>
          Nueva cuenta bancaria
        </Link>
      </header>

      {error ? (
        <div
          role="alert"
          className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700"
        >
          {error}
        </div>
      ) : null}

      {summary ? (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <Card className="bg-gradient-to-br from-amber-50 via-white to-white">
            <CardHeader>
              <CardDescription>Saldo total</CardDescription>
              <CardTitle className="text-2xl tabular-nums text-amber-950">
                {formatCurrency(summary.total_balance, "COP")}
              </CardTitle>
            </CardHeader>
          </Card>
          <Card className="bg-gradient-to-br from-emerald-50 via-white to-white">
            <CardHeader>
              <CardDescription>Conciliado</CardDescription>
              <CardTitle className="text-2xl tabular-nums text-emerald-800">
                {formatCurrency(summary.total_reconciled_balance, "COP")}
              </CardTitle>
            </CardHeader>
          </Card>
          <Card className="bg-gradient-to-br from-amber-50 via-white to-white">
            <CardHeader>
              <CardDescription>Pendiente por conciliar</CardDescription>
              <CardTitle className="text-2xl tabular-nums text-amber-800">
                {formatCurrency(summary.total_unreconciled_balance, "COP")}
              </CardTitle>
              <p className="text-xs text-slate-500">
                {summary.unreconciled_transactions} movimiento
                {summary.unreconciled_transactions === 1 ? "" : "s"}
              </p>
            </CardHeader>
          </Card>
          <Card className="bg-gradient-to-br from-slate-50 via-white to-white">
            <CardHeader>
              <CardDescription>Cuentas activas</CardDescription>
              <CardTitle className="text-2xl tabular-nums text-slate-900">
                {summary.active_accounts}
                <span className="text-base font-medium text-slate-500">
                  {" "}
                  / {summary.total_accounts}
                </span>
              </CardTitle>
            </CardHeader>
          </Card>
        </div>
      ) : null}

      <Card>
        <CardHeader>
          <CardTitle>Cuentas bancarias</CardTitle>
          <CardDescription>
            {accounts.length} cuenta{accounts.length === 1 ? "" : "s"}{" "}
            registrada{accounts.length === 1 ? "" : "s"}.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {accounts.length === 0 ? (
            <div className="rounded-xl border border-dashed border-slate-300 bg-slate-50 px-6 py-10 text-center">
              <p className="font-medium text-slate-700">
                Todavía no hay cuentas bancarias
              </p>
              <p className="mt-1 text-sm text-slate-500">
                Crea la primera cuenta para empezar a registrar movimientos.
              </p>
            </div>
          ) : (
            <Table>
              <caption className="sr-only">Cuentas bancarias</caption>
              <TableHeader>
                <TableRow>
                  <TableHead>Cuenta</TableHead>
                  <TableHead>Banco</TableHead>
                  <TableHead>Tipo</TableHead>
                  <TableHead>PUC</TableHead>
                  <TableHead className="text-right">Saldo</TableHead>
                  <TableHead>Estado</TableHead>
                  <TableHead className="text-right">Acciones</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {accounts.map((account) => (
                  <TableRow key={account.id}>
                    <TableCell className="text-slate-900">
                      {account.name}
                      <span className="block text-xs text-slate-500">
                        {account.account_number}
                      </span>
                    </TableCell>
                    <TableCell className="text-slate-900">
                      {account.bank_name}
                    </TableCell>
                    <TableCell className="text-slate-600">
                      {accountTypeLabels[account.account_type] ??
                        account.account_type}
                    </TableCell>
                    <TableCell className="text-slate-600">
                      {account.accounting_account_code}
                    </TableCell>
                    <TableCell className="text-right font-medium tabular-nums text-slate-950">
                      {formatCurrency(account.balance, account.currency)}
                    </TableCell>
                    <TableCell>
                      <span
                        className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-semibold ring-1 ring-inset ${
                          account.is_active
                            ? "bg-emerald-50 text-emerald-700 ring-emerald-200"
                            : "bg-slate-100 text-slate-600 ring-slate-200"
                        }`}
                      >
                        {account.is_active ? "Activa" : "Inactiva"}
                      </span>
                    </TableCell>
                    <TableCell className="text-right">
                      <Link
                        href={`/treasury/accounts/${account.id}`}
                        className="text-sm font-semibold text-amber-600 transition-colors hover:text-amber-800"
                      >
                        Ver detalle
                      </Link>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
