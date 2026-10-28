"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Cookie } from "lucide-react";

const STORAGE_KEY = "nexus-cookie-consent";

async function registerConsent(type: string, granted: boolean) {
  try {
    await fetch("/api/v1/consent", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify({ consent_type: type, is_granted: granted }),
    });
  } catch {
    // Sin conexión: el banner vuelve a mostrarse en la próxima visita.
  }
}

/** Banner flotante de consentimiento (GDPR/CCPA, estilo Black & Gold). */
export function CookieBanner() {
  const [visible, setVisible] = useState(false);
  const [details, setDetails] = useState(false);

  useEffect(() => {
    // SetState asíncrono: evitar setState síncrono en el efecto (React Compiler).
    const frame = requestAnimationFrame(() => {
      if (!window.localStorage.getItem(STORAGE_KEY)) setVisible(true);
    });
    return () => cancelAnimationFrame(frame);
  }, []);

  if (!visible) return null;

  function decide(analytics: boolean, marketing: boolean) {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify({ analytics, marketing, at: new Date().toISOString() }));
    registerConsent("cookies_analytics", analytics);
    registerConsent("cookies_marketing", marketing);
    setVisible(false);
  }

  return (
    <div className="fixed inset-x-0 bottom-0 z-[70] border-t-2 border-amber-500 bg-zinc-950/95 p-4 text-white shadow-2xl backdrop-blur">
      <div className="mx-auto flex max-w-6xl flex-wrap items-center gap-4">
        <Cookie className="size-6 shrink-0 text-amber-400" aria-hidden="true" />
        <p className="min-w-0 flex-1 text-sm leading-6 text-zinc-200">
          Usamos cookies esenciales para mantener tu sesión. Las analíticas y
          de marketing son opcionales. Consulta nuestra{" "}
          <Link href="/privacy" className="font-semibold text-amber-400 hover:underline">
            política de privacidad
          </Link>{" "}
          y los{" "}
          <Link href="/terms" className="font-semibold text-amber-400 hover:underline">
            términos
          </Link>
          .
        </p>
        <div className="flex flex-wrap gap-2">
          {details ? (
            <button type="button" onClick={() => decide(true, true)} className="rounded-lg bg-amber-500 px-4 py-2 text-sm font-semibold text-zinc-950 hover:bg-amber-400">
              Guardar preferencias (todo activado)
            </button>
          ) : (
            <button type="button" onClick={() => decide(true, true)} className="rounded-lg bg-amber-500 px-4 py-2 text-sm font-semibold text-zinc-950 hover:bg-amber-400">
              Aceptar todo
            </button>
          )}
          <button type="button" onClick={() => decide(false, false)} className="rounded-lg border border-zinc-700 px-4 py-2 text-sm font-semibold text-zinc-200 hover:bg-zinc-900">
            Solo esenciales
          </button>
          <button type="button" onClick={() => setDetails((prev) => !prev)} className="rounded-lg px-3 py-2 text-sm font-semibold text-amber-400 hover:bg-zinc-900">
            {details ? "Ocultar" : "Configurar"}
          </button>
        </div>
      </div>
      {details ? (
        <div className="mx-auto mt-2 max-w-6xl text-xs text-zinc-400">
          Esenciales: siempre activas (sesión). Analíticas y marketing: se
          registran en la base de datos tu elección con fecha y hora como
          evidencia de cumplimiento.
        </div>
      ) : null}
    </div>
  );
}
