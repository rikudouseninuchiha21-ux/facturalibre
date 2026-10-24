import type { Metadata } from "next";
import Link from "next/link";
import type { ReactNode } from "react";

import { LogoutButton } from "@/components/auth/LogoutButton";
import { getCurrentUser, type User } from "@/lib/api";
import { getSessionCookieHeader } from "@/lib/server-auth";

import "./globals.css";

export const metadata: Metadata = {
  title: {
    default: "FacturaLibre - MVP",
    template: "%s | FacturaLibre",
  },
  description: "Interfaz administrativa del MVP de facturación de FacturaLibre.",
};

const navigation = [
  { href: "/contacts", label: "Contactos", roles: ["ADMIN", "ACCOUNTANT", "CASHIER"] },
  { href: "/items", label: "Ítems", roles: ["ADMIN", "ACCOUNTANT", "CASHIER"] },
  { href: "/taxes", label: "Impuestos", roles: ["ADMIN", "ACCOUNTANT", "CASHIER"] },
  { href: "/invoices", label: "Facturas", roles: ["ADMIN", "ACCOUNTANT"] },
  { href: "/warehouses", label: "Bodegas", roles: ["ADMIN", "ACCOUNTANT", "CASHIER"] },
  { href: "/inventory", label: "Inventario", roles: ["ADMIN", "ACCOUNTANT", "CASHIER"] },
  { href: "/employees", label: "Empleados", roles: ["ADMIN"] },
  { href: "/payroll", label: "Nómina", roles: ["ADMIN"] },
  { href: "/purchases", label: "Compras", roles: ["ADMIN", "ACCOUNTANT"] },
  { href: "/pos", label: "Punto de Venta", roles: ["ADMIN", "CASHIER"] },
  { href: "/reports/financials", label: "Reportes", roles: ["ADMIN", "ACCOUNTANT"] },
];

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
      <body className="flex min-h-full flex-col bg-slate-50 text-slate-950 antialiased">
        <header className="border-b border-slate-200 bg-white print:hidden">
          <div className="mx-auto flex w-full max-w-6xl items-center justify-between gap-6 px-4 py-4 sm:px-6 lg:px-8">
            <Link
              href="/"
              className="flex shrink-0 items-center gap-2 text-lg font-semibold tracking-tight"
            >
              <span
                aria-hidden="true"
                className="flex size-8 items-center justify-center rounded-lg bg-slate-900 text-sm font-bold text-white"
              >
                FL
              </span>
              FacturaLibre
            </Link>

            <div className="flex flex-wrap items-center justify-end gap-3">
              {currentUser ? (
                <nav
                  aria-label="Navegación principal"
                  className="flex flex-wrap items-center justify-end gap-1 text-sm font-medium"
                >
                  {navigation
                    .filter((item) => item.roles.includes(currentUser.role))
                    .map((item) => (
                      <Link
                        key={item.href}
                        href={item.href}
                        className="rounded-lg px-3 py-2 text-slate-600 transition-colors hover:bg-slate-100 hover:text-slate-950"
                      >
                        {item.label}
                      </Link>
                    ))}
                </nav>
              ) : null}

              {currentUser ? (
                <div className="flex items-center gap-3 border-slate-200 pl-0 sm:border-l sm:pl-3">
                  <div className="flex flex-col">
                    <span
                      title={currentUser.email}
                      className="max-w-40 truncate text-sm font-medium text-slate-950"
                    >
                      {currentUser.full_name}
                    </span>
                    <span
                      className={`text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded ${
                        currentUser.role === "ADMIN"
                          ? "bg-blue-100 text-blue-700"
                          : currentUser.role === "ACCOUNTANT"
                            ? "bg-emerald-100 text-emerald-700"
                            : "bg-slate-100 text-slate-700"
                      }`}
                    >
                      {currentUser.role}
                    </span>
                  </div>
                  <LogoutButton />
                </div>
              ) : null}
            </div>
          </div>
        </header>

        <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-10 sm:px-6 lg:px-8">
          {children}
        </main>

        <footer className="border-t border-slate-200 bg-white">
          <div className="mx-auto w-full max-w-6xl px-4 py-5 text-sm text-slate-500 sm:px-6 lg:px-8">
            FacturaLibre MVP · Fase 10
          </div>
        </footer>
      </body>
    </html>
  );
}
