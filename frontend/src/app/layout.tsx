import type { Metadata } from "next";
import Link from "next/link";
import type { ReactNode } from "react";

import "./globals.css";

export const metadata: Metadata = {
  title: {
    default: "FacturaLibre - MVP",
    template: "%s | FacturaLibre",
  },
  description: "Interfaz administrativa del MVP de facturación de FacturaLibre.",
};

const navigation = [
  { href: "/contacts", label: "Contactos" },
  { href: "/invoices", label: "Facturas" },
  { href: "/warehouses", label: "Bodegas" },
  { href: "/inventory", label: "Inventario" },
  { href: "/employees", label: "Empleados" },
  { href: "/payroll", label: "Nómina" },
];

export default function RootLayout({
  children,
}: Readonly<{ children: ReactNode }>) {
  return (
    <html lang="es" className="h-full">
      <body className="flex min-h-full flex-col bg-slate-50 text-slate-950 antialiased">
        <header className="border-b border-slate-200 bg-white">
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

            <nav
              aria-label="Navegación principal"
              className="flex flex-wrap items-center justify-end gap-1 text-sm font-medium"
            >
              {navigation.map((item) => (
                <Link
                  key={item.href}
                  href={item.href}
                  className="rounded-lg px-3 py-2 text-slate-600 transition-colors hover:bg-slate-100 hover:text-slate-950"
                >
                  {item.label}
                </Link>
              ))}
            </nav>
          </div>
        </header>

        <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-10 sm:px-6 lg:px-8">
          {children}
        </main>

        <footer className="border-t border-slate-200 bg-white">
          <div className="mx-auto w-full max-w-6xl px-4 py-5 text-sm text-slate-500 sm:px-6 lg:px-8">
            FacturaLibre MVP · Fase 5C-2
          </div>
        </footer>
      </body>
    </html>
  );
}
