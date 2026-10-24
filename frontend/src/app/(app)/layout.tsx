import type { Metadata } from "next";
import type { ReactNode } from "react";

import { getCurrentUser, type User } from "@/lib/api";
import { getSessionCookieHeader } from "@/lib/server-auth";
import { Sidebar } from "@/components/layout/Sidebar";
import { Topbar } from "@/components/layout/Topbar";

import "../globals.css";

export const metadata: Metadata = {
  title: {
    default: "Nexus ERP",
    template: "%s | Nexus ERP",
  },
  description: "Interfaz administrativa de Nexus ERP.",
};

export default async function AppLayout({
  children,
}: Readonly<{ children: ReactNode }>) {
  let currentUser: User | null = null;
  const cookieHeader = await getSessionCookieHeader();

  if (cookieHeader) {
    try {
      currentUser = await getCurrentUser(cookieHeader);
    } catch {
      // La cookie puede estar expirada; el backend seguirá devolviendo 401 en
      // las llamadas de negocio y el middleware redirige si no hay cookie.
      currentUser = null;
    }
  }

  return (
    <div className="flex h-screen w-full overflow-hidden bg-zinc-50">
      {/* Sidebar */}
      <Sidebar currentUser={currentUser} />

      {/* Contenedor Derecho */}
      <div className="flex flex-1 flex-col overflow-hidden">
        {/* Topbar (Fijo arriba, no se mueve con el scroll) */}
        <div className="shrink-0 z-50">
          <Topbar currentUser={currentUser} />
        </div>

        {/* Main (Hace scroll independiente por debajo del topbar) */}
        <main className="flex-1 overflow-y-auto p-4 md:p-8 lg:p-12">
          {children}
        </main>

        {/* Footer (Fijo abajo) */}
        <footer className="shrink-0 border-t border-zinc-200 bg-white px-8 py-4 text-sm text-zinc-500">
          Nexus ERP · Fase 22
        </footer>
      </div>
    </div>
  );
}
