import type { Metadata } from "next";
import type { ReactNode } from "react";

import { getCurrentUser, type User } from "@/lib/api";
import { getSessionCookieHeader } from "@/lib/server-auth";
import { Sidebar } from "@/components/layout/Sidebar";
import { Topbar } from "@/components/layout/Topbar";

import "./globals.css";

export const metadata: Metadata = {
  title: {
    default: "Nexus ERP",
    template: "%s | Nexus ERP",
  },
  description: "Interfaz administrativa de Nexus ERP.",
};

export default async function RootLayout({
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
    <html lang="es" className="h-full">
      <body className="flex min-h-screen bg-zinc-50 text-zinc-900 antialiased">
        {/* Sidebar */}
        <Sidebar currentUser={currentUser} />

        {/* Main content wrapper */}
        <div className="flex-1 flex-col min-h-0 bg-zinc-50">
          <Topbar currentUser={currentUser} />

          <main className="flex-1 p-4 md:p-8 lg:p-12 overflow-y-auto">
            {children}
          </main>

          <footer className="border-t border-zinc-200 bg-white px-8 py-5 text-sm text-zinc-500">
            Nexus ERP · Fase 22
          </footer>
        </div>
      </body>
    </html>
  );
}
