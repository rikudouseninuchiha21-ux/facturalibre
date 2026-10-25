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
  getExpenses,
  type Expense,
} from "@/lib/api";
import { getSessionCookieHeader } from "@/lib/server-auth";
import { formatCurrency } from "@/lib/format";

export const dynamic = "force-dynamic";

export const metadata: Metadata = {
  title: "Gastos",
};

const paymentMethodLabels: Record<string, string> = {
  cash: "Efectivo",
  transfer: "Transferencia",
};

export default async function ExpensesPage() {
  const cookieHeader = await getSessionCookieHeader();

  let expenses: Expense[] = [];
  let error: string | null = null;

  try {
    expenses = await getExpenses(cookieHeader);
  } catch (cause) {
    error =
      cause instanceof Error
        ? cause.message
        : "No se pudo consultar el listado de gastos.";
  }

  return (
    <div className="space-y-6">
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-slate-950">
            Gastos Operativos
          </h1>
          <p className="mt-2 max-w-2xl text-slate-600">
            Gastos registrados: arriendo, servicios, papelería y otros gastos
            de operación. Cada gasto genera su asiento contable automático.
          </p>
        </div>
        <Link
          href="/expenses/new"
          className="inline-flex items-center justify-center gap-2 rounded-lg bg-slate-900 px-4 py-2 text-sm font-semibold text-white shadow-sm transition-colors hover:bg-slate-700 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-slate-900"
        >
          <span aria-hidden="true">+</span>
          Nuevo gasto
        </Link>
      </header>

      <Card>
        <CardHeader>
          <CardTitle>Listado</CardTitle>
          <CardDescription>
            {error
              ? "No fue posible obtener los datos."
              : `${expenses.length} gasto${expenses.length === 1 ? "" : "s"} encontrada${expenses.length === 1 ? "" : "s"}.`}
          </CardDescription>
        </CardHeader>
        <CardContent>
          {error ? (
            <div
              role="alert"
              className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700"
            >
              {error}
            </div>
          ) : expenses.length === 0 ? (
            <div className="rounded-xl border border-dashed border-slate-300 bg-slate-50 px-6 py-10 text-center">
              <p className="font-medium text-slate-700">
                Todavía no hay gastos registrados
              </p>
              <p className="mt-1 text-sm text-slate-500">
                Usa el botón “Nuevo gasto” para registrar el primero.
              </p>
            </div>
          ) : (
            <Table>
              <caption className="sr-only">Listado de gastos operativos</caption>
              <TableHeader>
                <TableRow>
                  <TableHead>Fecha</TableHead>
                  <TableHead>Concepto</TableHead>
                  <TableHead>Método</TableHead>
                  <TableHead className="text-right">Monto</TableHead>
                  <TableHead className="text-right">Referencia</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {expenses.map((expense) => (
                  <TableRow key={expense.id}>
                    <TableCell className="text-slate-900">
                      {expense.date}
                    </TableCell>
                    <TableCell className="text-slate-900">
                      {expense.concept}
                    </TableCell>
                    <TableCell className="text-slate-900">
                      {paymentMethodLabels[expense.payment_method] ?? expense.payment_method}
                    </TableCell>
                    <TableCell className="text-right font-medium tabular-nums text-slate-950">
                      {formatCurrency(expense.amount, "COP")}
                    </TableCell>
                    <TableCell className="text-right text-slate-600">
                      {expense.reference ?? "—"}
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
