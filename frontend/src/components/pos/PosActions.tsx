"use client";

interface PosActionsProps {
  label?: string;
}

/**
 * Acciones interactivas del POS.
 *
 * Se aísla en un Client Component porque la página es un Server Component que
 * consulta los contactos en el servidor y no puede pasar manejadores de eventos
 * a componentes de cliente.
 */
export function PosActions({ label = "Reintentar" }: PosActionsProps) {
  return (
    <button
      type="button"
      onClick={() => window.location.reload()}
      className="inline-flex items-center justify-center rounded-lg bg-slate-900 px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-slate-700"
    >
      {label}
    </button>
  );
}
