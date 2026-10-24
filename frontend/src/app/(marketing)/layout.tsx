import type { Metadata } from "next";
import type { ReactNode } from "react";

import "../globals.css";

export const metadata: Metadata = {
  title: {
    default: "Nexus ERP",
    template: "%s | Nexus ERP",
  },
  description: "El ERP para facturación, inventario, nómina y contabilidad de tu empresa en Colombia.",
};

export default function MarketingLayout({
  children,
}: Readonly<{ children: ReactNode }>) {
  return (
    <div className="flex min-h-screen flex-col bg-white text-zinc-900 antialiased">
      {children}
    </div>
  );
}
