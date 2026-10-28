import type { Metadata } from "next";
import { notFound } from "next/navigation";

import { BudgetDetailClient } from "@/components/budgets/BudgetDetailClient";
import {
  getBudget,
  getLedgerAccounts,
  type AccountingAccount,
  type Budget,
} from "@/lib/api";
import { getSessionCookieHeader } from "@/lib/server-auth";

export const dynamic = "force-dynamic";

export async function generateMetadata({
  params,
}: {
  params: Promise<{ id: string }>;
}): Promise<Metadata> {
  const { id } = await params;
  const cookieHeader = await getSessionCookieHeader();
  try {
    const budget = await getBudget(id, cookieHeader);
    const label =
      budget.name ??
      `${String(budget.period_month).padStart(2, "0")}/${budget.period_year}`;
    return { title: `Presupuesto ${label}` };
  } catch {
    return { title: "Presupuesto" };
  }
}

export default async function BudgetDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const cookieHeader = await getSessionCookieHeader();

  let budget: Budget | null = null;
  let accounts: AccountingAccount[] = [];

  try {
    budget = await getBudget(id, cookieHeader);
  } catch {
    notFound();
  }

  try {
    accounts = await getLedgerAccounts(undefined, cookieHeader);
  } catch {
    accounts = [];
  }

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-3xl font-bold tracking-tight text-slate-950">
          Presupuesto {budget.cost_center.name}
        </h1>
        <p className="mt-2 max-w-2xl text-slate-600">
          {String(budget.period_month).padStart(2, "0")}/{budget.period_year} ·{" "}
          {budget.cost_center.code} · Estado {budget.status}
        </p>
      </header>

      <BudgetDetailClient initialBudget={budget} accounts={accounts} />
    </div>
  );
}
