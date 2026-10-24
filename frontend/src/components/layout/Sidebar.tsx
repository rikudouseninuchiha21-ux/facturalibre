"use client";

import Link from "next/link";
import { useState } from "react";

import { type User } from "@/lib/api";
import {
  BarChart3,
  FileText,
  GraduationCap,
  LayoutDashboard,
  Package,
  Percent,
  Settings,
  ShoppingCart,
  Users,
  Warehouse,
} from "lucide-react";

interface SidebarProps {
  currentUser: User | null;
}

const NAVIGATION = [
  {
    label: "Inicio",
    items: [
      {
        href: "/dashboard",
        label: "Panel",
        icon: LayoutDashboard,
        roles: ["ADMIN", "ACCOUNTANT", "CASHIER"],
      },
    ],
  },
  {
    label: "Operaciones",
    items: [
      { href: "/pos", label: "Punto de Venta", icon: ShoppingCart, roles: ["ADMIN", "CASHIER"] },
      { href: "/invoices", label: "Ventas", icon: FileText, roles: ["ADMIN", "ACCOUNTANT"] },
      { href: "/purchases", label: "Compras", icon: Package, roles: ["ADMIN", "ACCOUNTANT"] },
    ],
  },
  {
    label: "Catálogos",
    items: [
      { href: "/contacts", label: "Contactos", icon: Users, roles: ["ADMIN", "ACCOUNTANT", "CASHIER"] },
      { href: "/items", label: "Ítems", icon: Package, roles: ["ADMIN", "ACCOUNTANT", "CASHIER"] },
    ],
  },
  {
    label: "Contabilidad",
    items: [
      { href: "/reports/financials", label: "Reportes", icon: BarChart3, roles: ["ADMIN", "ACCOUNTANT"] },
    ],
  },
  {
    label: "Administración",
    items: [
      { href: "/payroll", label: "Nómina", icon: GraduationCap, roles: ["ADMIN"] },
      { href: "/employees", label: "Empleados", icon: Users, roles: ["ADMIN"] },
      { href: "/warehouses", label: "Bodegas", icon: Warehouse, roles: ["ADMIN", "ACCOUNTANT", "CASHIER"] },
      { href: "/taxes", label: "Impuestos", icon: Percent, roles: ["ADMIN", "ACCOUNTANT"] },
      { href: "/settings", label: "Configuración", icon: Settings, roles: ["ADMIN"] },
    ],
  },
];

export function Sidebar({ currentUser }: SidebarProps) {
  const [isCollapsed, setIsCollapsed] = useState(false);

  return (
    <aside
      className="w-64 bg-white border-r border-zinc-200 text-zinc-950 z-50 shrink-0 flex flex-col h-full"
    >
      {/* Sidebar header with logo */}
      <div className="flex items-center justify-between px-4 py-6 border-b border-zinc-200 bg-white shrink-0">
        <div className="flex items-center gap-2">
          <div className="flex size-8 items-center justify-center rounded-full bg-indigo-600 text-xs font-bold text-white shadow-lg shadow-indigo-500/30">
            N
          </div>
          <span className={isCollapsed ? "hidden" : "text-lg font-bold tracking-tight text-zinc-950"}>
            Nexus ERP
          </span>
        </div>
        <button
          type="button"
          onClick={() => setIsCollapsed((prev) => !prev)}
          aria-label="Colapsar menú"
          className="md:hidden p-2 rounded-md text-zinc-600 hover:bg-zinc-100 hover:text-zinc-900 transition-colors"
        >
          <svg
            className={`size-5 ${isCollapsed ? "-rotate-90" : ""}`}
            xmlns="http://www.w3.org/2000/svg"
            fill="none"
            viewBox="0 0 24 24"
            strokeWidth={2.5}
            stroke="currentColor"
          >
            <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
          </svg>
        </button>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-2 py-3 overflow-y-auto">
        {NAVIGATION.map((category) => {
          const items = category.items.filter((i) =>
            currentUser ? i.roles.includes(currentUser.role) : false
          );
          if (items.length === 0) return null;

          return (
            <div key={category.label}>
              <h3 className="px-3 py-2 text-[10px] font-bold uppercase tracking-wider text-zinc-500">
                {category.label}
              </h3>
              <ul className="space-y-0.5">
                {items.map((item) => (
                  <Link
                    key={item.href}
                    href={item.href}
                    className={`flex items-center gap-3 px-3 py-2 rounded-md text-sm transition-colors ${
                      currentUser?.role === "ADMIN"
                        ? "text-zinc-400 hover:text-white hover:bg-zinc-800/50"
                        : "text-zinc-400 hover:text-white hover:bg-zinc-800/50"
                    }`}
                  >
                    <item.icon className="size-4 shrink-0" />
                    {isCollapsed ? (
                      <span className="sr-only">{item.label}</span>
                    ) : (
                      <span className="truncate">{item.label}</span>
                    )}
                  </Link>
                ))}
              </ul>
            </div>
          );
        })}
      </nav>

      {/* Footer with user profile */}
      <div className="shrink-0 p-4 border-t border-zinc-800 bg-white">
        <div className="flex items-center justify-between w-full gap-2">
          <div className="flex items-center gap-3 min-w-0">
            <div className="flex size-9 shrink-0 items-center justify-center rounded-full bg-indigo-600/10 text-indigo-400 text-sm font-bold border border-indigo-500/20">
              {currentUser?.full_name?.charAt(0) || "U"}
            </div>
            <div className="flex flex-col min-w-0">
              <span className="text-sm font-medium text-zinc-900 truncate">
                {currentUser?.full_name}
              </span>
              <span className="text-[10px] font-semibold text-indigo-400 uppercase tracking-wider">
                {currentUser?.role}
              </span>
            </div>
          </div>
        </div>
      </div>
    </aside>
  );
}
