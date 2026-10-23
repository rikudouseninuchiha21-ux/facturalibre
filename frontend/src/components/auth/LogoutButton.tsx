"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { ApiError, logout } from "@/lib/api";

export function LogoutButton() {
  const router = useRouter();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleLogout(): Promise<void> {
    setError(null);
    setIsSubmitting(true);

    try {
      await logout();
      router.replace("/login");
      router.refresh();
    } catch (cause) {
      setError(
        cause instanceof ApiError
          ? cause.message
          : "No se pudo cerrar la sesión.",
      );
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="flex flex-col items-end gap-1">
      <button
        type="button"
        onClick={handleLogout}
        disabled={isSubmitting}
        aria-busy={isSubmitting}
        className="rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 shadow-sm transition-colors hover:border-slate-400 hover:bg-slate-50 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-slate-900 disabled:cursor-wait disabled:opacity-60"
      >
        {isSubmitting ? "Saliendo..." : "Cerrar Sesión"}
      </button>

      {error ? (
        <p role="alert" className="text-right text-xs text-red-600">
          {error}
        </p>
      ) : null}
    </div>
  );
}
