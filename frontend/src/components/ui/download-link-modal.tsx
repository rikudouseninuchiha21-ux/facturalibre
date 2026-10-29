"use client";

import { Download } from "lucide-react";

import { Modal } from "@/components/ui/modal";

interface DownloadLinkModalProps {
  /** Título del modal. */
  title: string;
  /** Texto explicativo bajo el título. */
  description?: string;
  /** URL real del endpoint del backend. */
  url: string;
  /** Nombre sugerido del archivo (incluye extensión). */
  fileName: string;
  onClose: () => void;
}

/**
 * Modal con un botón de descarga directa.
 *
 * Chrome bloquea en localhost las descargas que abren una pestaña nueva
 * (`target="_blank"`). Aquí el clic del usuario crea un enlace temporal sin
 * `target`, le asigna `download` y lo pulsa de forma síncrona: la descarga se
 * hace en la misma pestaña y el bloqueador de ventanas emergentes no interviene.
 * El modal sirve además como confirmación visual: si la descarga automática no
 * hacía nada, el usuario ve el botón y sabe que debe pulsarlo.
 */
export function DownloadLinkModal({
  title,
  description,
  url,
  fileName,
  onClose,
}: DownloadLinkModalProps) {
  function handleDownload(): void {
    const link = document.createElement("a");
    link.href = url;
    link.download = fileName;
    link.rel = "noopener";
    link.style.display = "none";
    document.body.appendChild(link);
    link.click();
    // Retirar el ancla en el siguiente tick: quitarla de forma síncrona puede
    // cancelar la descarga en Chromium antes de que el navegador la registre.
    window.setTimeout(() => link.remove(), 1_000);
  }

  return (
    <Modal
      title={title}
      description={description}
      onClose={onClose}
      maxWidthClassName="max-w-lg"
    >
      <div className="space-y-4">
        <div className="rounded-xl border border-violet-200 bg-violet-50 px-4 py-3 text-sm text-violet-900">
          <p className="font-semibold">
            El navegador no inició la descarga automáticamente.
          </p>
          <p className="mt-1 text-violet-800">
            Pulsa el botón para guardar{" "}
            <span className="break-all font-mono text-xs font-semibold">
              {fileName}
            </span>
            .
          </p>
        </div>

        <button
          type="button"
          onClick={handleDownload}
          className="inline-flex w-full items-center justify-center gap-2 rounded-lg bg-violet-600 px-4 py-3 text-sm font-semibold text-white shadow-sm transition-colors hover:bg-violet-500 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-violet-600"
        >
          <Download className="size-4" aria-hidden="true" />
          Haz clic para descargar
        </button>

        <p className="text-xs leading-relaxed text-slate-500">
          La descarga se guardará directamente, sin abrir pestañas nuevas. Si el
          archivo no aparece, revisa la barra de descargas o la carpeta{" "}
          <code>~/Descargas</code>.
        </p>

        <div className="flex justify-end">
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 transition-colors hover:bg-slate-50"
          >
            Cerrar
          </button>
        </div>
      </div>
    </Modal>
  );
}
