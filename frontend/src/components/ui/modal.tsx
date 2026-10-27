"use client";

import type { ReactNode } from "react";
import { X } from "lucide-react";

interface ModalProps {
  title: string;
  description?: string;
  onClose: () => void;
  children: ReactNode;
  /** Ancho máximo del panel (clases max-w-* de Tailwind). */
  maxWidthClassName?: string;
}

/**
 * Modal flotante reutilizable (overlay + panel + botón cerrar).
 * Los modales no empujan el contenido de la página: el formulario que
 * contienen vive en su propio scroll.
 */
export function Modal({
  title,
  description,
  onClose,
  children,
  maxWidthClassName = "max-w-xl",
}: ModalProps) {
  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center bg-zinc-950/50 p-4">
      <div
        role="dialog"
        aria-modal="true"
        aria-label={title}
        className={`max-h-[90vh] w-full ${maxWidthClassName} overflow-y-auto rounded-2xl border border-zinc-200 bg-white shadow-2xl`}
      >
        <div className="sticky top-0 flex items-start justify-between gap-4 border-b border-zinc-100 bg-white px-6 py-4">
          <div>
            <h2 className="text-lg font-semibold text-zinc-950">{title}</h2>
            {description ? (
              <p className="mt-1 text-sm text-zinc-500">{description}</p>
            ) : null}
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Cerrar"
            className="rounded-lg p-1.5 text-zinc-500 transition-colors hover:bg-zinc-100 hover:text-zinc-900"
          >
            <X className="size-5" aria-hidden="true" />
          </button>
        </div>
        <div className="px-6 py-5">{children}</div>
      </div>
    </div>
  );
}
