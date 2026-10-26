import { formatCurrency } from "@/lib/format";
import type { AgingBuckets } from "@/lib/api";

interface BucketCardsProps {
  buckets: AgingBuckets;
  compact?: boolean;
}

const BUCKETS = [
  {
    key: "current",
    label: "Corriente",
    hint: "Aún no vence",
    card: "border-emerald-200 bg-emerald-50",
    text: "text-emerald-800",
    dot: "bg-emerald-500",
  },
  {
    key: "d0_30",
    label: "0 – 30 días",
    hint: "Vencido reciente",
    card: "border-amber-100 bg-amber-50",
    text: "text-amber-800",
    dot: "bg-amber-300",
  },
  {
    key: "d31_60",
    label: "31 – 60 días",
    hint: "Requiere gestión",
    card: "border-amber-200 bg-amber-100/70",
    text: "text-amber-900",
    dot: "bg-amber-500",
  },
  {
    key: "d61_90",
    label: "61 – 90 días",
    hint: "Riesgo alto",
    card: "border-orange-200 bg-orange-50",
    text: "text-orange-900",
    dot: "bg-orange-500",
  },
  {
    key: "d91_120",
    label: "91 – 120 días",
    hint: "Cobro urgente",
    card: "border-red-200 bg-red-50",
    text: "text-red-800",
    dot: "bg-red-400",
  },
  {
    key: "d120_plus",
    label: "120+ días",
    hint: "Cartera crítica",
    card: "border-red-300 bg-red-100/70",
    text: "text-red-900",
    dot: "bg-red-600",
  },
] as const;

export function BucketCards({ buckets, compact = false }: BucketCardsProps) {
  return (
    <div
      className={`grid gap-3 ${
        compact ? "sm:grid-cols-3 lg:grid-cols-6" : "sm:grid-cols-2 lg:grid-cols-3"
      }`}
    >
      {BUCKETS.map((bucket) => (
        <div
          key={bucket.key}
          className={`rounded-xl border p-4 ${bucket.card}`}
        >
          <div className="flex items-center gap-2">
            <span className={`size-2.5 rounded-full ${bucket.dot}`} aria-hidden="true" />
            <p className="text-xs font-semibold uppercase tracking-wide text-zinc-600">
              {bucket.label}
            </p>
          </div>
          <p className={`mt-2 text-xl font-bold tabular-nums ${bucket.text}`}>
            {formatCurrency(buckets[bucket.key])}
          </p>
          <p className="mt-1 text-xs text-zinc-500">{bucket.hint}</p>
        </div>
      ))}
    </div>
  );
}
