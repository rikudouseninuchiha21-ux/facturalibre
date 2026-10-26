import type { DianDocumentStatus } from "@/lib/api";

const STATUS_CONFIG: Record<
  DianDocumentStatus,
  { label: string; className: string }
> = {
  BORRADOR: {
    label: "Borrador",
    className: "bg-zinc-100 text-zinc-600 ring-zinc-200",
  },
  GENERADO: {
    label: "Generado",
    className: "bg-emerald-50 text-emerald-700 ring-emerald-200",
  },
  GENERADO_SIN_PIN: {
    label: "Generado sin PIN",
    className: "bg-amber-50 text-amber-800 ring-amber-200",
  },
  ENVIADO: {
    label: "Enviado a DIAN",
    className: "bg-blue-50 text-blue-700 ring-blue-200",
  },
  ACEPTADO: {
    label: "Aceptado",
    className: "bg-emerald-50 text-emerald-700 ring-emerald-200",
  },
  RECHAZADO: {
    label: "Rechazado",
    className: "bg-red-50 text-red-700 ring-red-200",
  },
};

const PENDING_STYLE = "bg-slate-100 text-slate-500 ring-slate-200";

interface InvoiceDianBadgeProps {
  dianStatus: DianDocumentStatus | null;
}

/** Badge del estado del documento electrónico DIAN de una factura. */
export function InvoiceDianBadge({ dianStatus }: InvoiceDianBadgeProps) {
  if (dianStatus === null) {
    return (
      <span
        className={`inline-flex items-center rounded-full px-2.5 py-1 text-xs font-semibold ring-1 ring-inset ${PENDING_STYLE}`}
        title="Aún no se ha generado el XML/PDF DIAN"
      >
        Pendiente de envío
      </span>
    );
  }

  const config = STATUS_CONFIG[dianStatus];
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-1 text-xs font-semibold ring-1 ring-inset ${config.className}`}
    >
      {config.label}
    </span>
  );
}
