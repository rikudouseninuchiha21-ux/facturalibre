import type { Metadata } from "next";
import type { ReactNode } from "react";

import { CookieBanner } from "@/components/layout/CookieBanner";

import "./globals.css";

export const metadata: Metadata = {
  title: {
    default: "VANTAGE - ERP",
    template: "%s | VANTAGE",
  },
  description: "Sistema de gestión empresarial VANTAGE",
};

export default function RootLayout({
  children,
}: Readonly<{ children: ReactNode }>) {
  return (
    <html lang="es" className="h-full">
      <body className="min-h-screen bg-white text-slate-900 antialiased">
        {children}
    <CookieBanner />
      </body>
    </html>
  );
}
