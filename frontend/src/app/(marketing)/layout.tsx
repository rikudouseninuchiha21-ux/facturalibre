import type { Metadata } from "next";
import type { ReactNode } from "react";

import "../globals.css";

export const metadata: Metadata = {
  title: {
    default: "VANTAGE - ERP",
    template: "%s | VANTAGE",
  },
  description: "Sistema de gestión empresarial VANTAGE",
};

export default function MarketingLayout({
  children,
}: Readonly<{ children: ReactNode }>) {
  return (
    <div className="flex min-h-screen flex-col bg-white text-slate-900 antialiased">
      {children}
    </div>
  );
}
