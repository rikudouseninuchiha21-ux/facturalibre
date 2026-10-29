"use client";

import { Building2, Search } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { LogoutButton } from "@/components/auth/LogoutButton";
import { NotificationsBell } from "@/components/notifications/NotificationsBell";
import { switchCompany, type User } from "@/lib/api";

interface TopbarProps {
  currentUser: User | null;
}

export function Topbar({ currentUser }: TopbarProps) {
  const router = useRouter();
  const [isSwitching, setIsSwitching] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleCompanyChange(companyId: string): Promise<void> {
    if (!companyId || companyId === currentUser?.active_company_id) {
      return;
    }
    setError(null);
    setIsSwitching(true);
    try {
      await switchCompany(companyId);
      router.refresh();
    } catch {
      setError("No se pudo cambiar de empresa.");
    } finally {
      setIsSwitching(false);
    }
  }

  return (
    <header className="z-30 flex h-16 items-center justify-between gap-4 px-6 py-2.5 bg-white border-b border-violet-100 shadow-sm shrink-0 print:hidden">
      <div className="flex min-w-0 items-center gap-4">
        <div className="hidden md:block md:w-72">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 size-4 text-slate-400 -translate-y-1/2" />
            <input
              type="text"
              placeholder="Buscar..."
              className="w-full pl-10 pr-4 py-2 rounded-lg border border-slate-200 bg-white text-sm text-slate-800 shadow-sm outline-none transition-all focus:border-violet-500 focus:ring-2 focus:ring-violet-500/20"
            />
          </div>
        </div>

        {currentUser && (currentUser.companies?.length ?? 0) > 0 ? (
          <div className="flex min-w-0 items-center gap-2">
            <Building2 className="size-4 shrink-0 text-violet-600" aria-hidden="true" />
            <select
              aria-label="Empresa activa"
              value={currentUser.active_company_id ?? ""}
              onChange={(event) => void handleCompanyChange(event.target.value)}
              disabled={isSwitching}
              className="max-w-[220px] truncate rounded-lg border border-violet-200 bg-violet-50 px-3 py-2 text-sm font-semibold text-violet-900 outline-none transition-colors hover:border-violet-300 focus:border-violet-500 focus:ring-2 focus:ring-violet-500/20 disabled:cursor-wait disabled:opacity-60"
            >
              {(currentUser.companies ?? []).map((company) => (
                <option key={company.id} value={company.id}>
                  {company.name}
                </option>
              ))}
            </select>
          </div>
        ) : null}
        {error ? (
          <span role="alert" className="text-xs font-medium text-red-600">
            {error}
          </span>
        ) : null}
      </div>

      <div className="flex items-center gap-3">
        {currentUser && (
          <div className="flex items-center gap-3 pl-4 border-l border-violet-100 shrink-0">
            <NotificationsBell />
            <div className="flex flex-col min-w-0">
              <span
                title={currentUser.full_name}
                className="max-w-[150px] truncate text-sm font-medium text-slate-800"
              >
                {currentUser.full_name}
              </span>
              <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded bg-violet-100 text-violet-800">
                {currentUser.role}
              </span>
            </div>
            <LogoutButton />
          </div>
        )}
      </div>
    </header>
  );
}
