import type { Metadata } from "next";
import Link from "next/link";

import { ExpenseForm } from "@/components/expenses/ExpenseForm";

export const dynamic = "force-dynamic";

export const metadata: Metadata = {
  title: "Nuevo gasto",
};

export default async function NewExpensePage() {
  return (
    <div className="space-y-6">
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <Link
            href="/expenses"
            className="text-sm font-medium text-blue-600 transition-colors hover:text-blue-700"
          >
            ← Volver a gastos
          </Link>
          <h1 className="mt-2 text-3xl font-bold tracking-tight text-slate-950">
            Nuevo gasto
          </h1>
          <p className="mt-2 max-w-2xl text-slate-600">
            Registra un gasto operativo (arriendo, servicios, papelería, etc.).
            Se generará automáticamente el asiento contable correspondiente.
          </p>
        </div>
      </header>

      <ExpenseForm />
    </div>
  );
}
