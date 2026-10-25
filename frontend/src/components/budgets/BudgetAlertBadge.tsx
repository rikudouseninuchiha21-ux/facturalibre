const ALERT_STYLES: Record<
  string,
  { label: string; className: string }
> = {
  OK: {
    label: "OK",
    className: "bg-slate-100 text-slate-600 ring-slate-300",
  },
  WARNING: {
    label: "Atención",
    className: "bg-amber-50 text-amber-700 ring-amber-300",
  },
  CRITICAL: {
    label: "Crítico",
    className: "bg-orange-100 text-orange-800 ring-orange-300",
  },
  OVER: {
    label: "Sobregiro",
    className: "bg-red-50 text-red-700 ring-red-300",
  },
  "N/A": {
    label: "Sin presupuesto",
    className: "bg-zinc-50 text-zinc-400 ring-zinc-200",
  },
};

interface BudgetAlertBadgeProps {
  level: string;
  utilizationPct?: string | null;
}

export function BudgetAlertBadge({ level, utilizationPct }: BudgetAlertBadgeProps) {
  const style = ALERT_STYLES[level] ?? ALERT_STYLES["N/A"];
  const tooltip =
    level === "N/A"
      ? "Cuenta sin presupuesto asignado"
      : `Utilizado ${utilizationPct ?? "0"}% del presupuesto`;

  return (
    <span
      title={tooltip}
      aria-label={tooltip}
      className={`inline-flex items-center rounded-full px-2.5 py-1 text-xs font-semibold ring-1 ring-inset ${style.className}`}
    >
      {style.label}
    </span>
  );
}
