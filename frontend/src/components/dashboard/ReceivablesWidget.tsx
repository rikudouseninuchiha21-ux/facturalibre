import Link from "next/link";
import { AlertCircle, ArrowRight, Clock, Receipt } from "lucide-react";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import type { ReceivablesSummary } from "@/lib/api";
import { formatCurrency } from "@/lib/format";

const OVERDUE_BUCKETS = [
  { key: "d0_30", label: "0 – 30 días", bar: "bg-violet-300" },
  { key: "d31_60", label: "31 – 60 días", bar: "bg-violet-500" },
  { key: "d61_90", label: "61 – 90 días", bar: "bg-orange-500" },
  { key: "d91_120", label: "91 – 120 días", bar: "bg-red-400" },
  { key: "d120_plus", label: "120+ días", bar: "bg-red-600" },
] as const;

export function ReceivablesWidget({ summary }: { summary: ReceivablesSummary }) {
  const hasOverdue = Number(summary.total_overdue) > 0;

  return (
    <Card className="border-violet-200 bg-gradient-to-br from-violet-50 to-white">
      <CardHeader className="flex flex-row items-center justify-between">
        <div>
          <CardTitle>Cartera vencida</CardTitle>
          <CardDescription>
            Saldo pendiente por vencimiento al {summary.as_of_date}.
          </CardDescription>
        </div>
        <div className="flex size-10 items-center justify-center rounded-xl bg-violet-100 text-violet-700">
          {hasOverdue ? (
            <AlertCircle className="size-5" aria-hidden="true" />
          ) : (
            <Receipt className="size-5" aria-hidden="true" />
          )}
        </div>
      </CardHeader>
      <CardContent>
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-zinc-500">
              Total vencido
            </p>
            <p
              className={`text-3xl font-bold tabular-nums ${
                hasOverdue ? "text-red-700" : "text-emerald-700"
              }`}
            >
              {formatCurrency(summary.total_overdue)}
            </p>
          </div>
          <Link
            href="/receivables"
            className="inline-flex items-center gap-1.5 text-sm font-semibold text-violet-700 transition-colors hover:text-violet-900"
          >
            Ver cartera
            <ArrowRight className="size-4" aria-hidden="true" />
          </Link>
        </div>

        {hasOverdue ? (
          <ul className="mt-4 space-y-2">
            {OVERDUE_BUCKETS.map((bucket) => (
              <li
                key={bucket.key}
                className="flex items-center justify-between gap-3 text-sm"
              >
                <span className="flex items-center gap-2 text-zinc-600">
                  <span
                    className={`h-2 w-6 rounded-full ${bucket.bar}`}
                    aria-hidden="true"
                  />
                  {bucket.label}
                </span>
                <span className="font-semibold tabular-nums text-zinc-900">
                  {formatCurrency(summary.buckets_totals[bucket.key])}
                </span>
              </li>
            ))}
          </ul>
        ) : (
          <div className="mt-4 flex items-center gap-3 rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3">
            <Clock className="size-5 text-emerald-600" aria-hidden="true" />
            <p className="text-sm font-medium text-emerald-800">
              No hay cartera vencida. Todo al día.
            </p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
