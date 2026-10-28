"use client";

import { Search } from "lucide-react";
import { LogoutButton } from "@/components/auth/LogoutButton";
import { NotificationsBell } from "@/components/notifications/NotificationsBell";

interface TopbarProps {
  currentUser: { full_name: string; role: string } | null;
}

export function Topbar({ currentUser }: TopbarProps) {
  return (
    <header className="z-30 flex h-16 items-center justify-between px-6 py-2.5 bg-white border-b border-violet-100 shadow-sm shrink-0 print:hidden">
      <div className="flex items-center gap-4">
        <div className="hidden md:flex-1 max-w-md">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 size-4 text-slate-400 -translate-y-1/2" />
            <input
              type="text"
              placeholder="Buscar..."
              className="w-full pl-10 pr-4 py-2 rounded-lg border border-slate-200 bg-white text-sm text-slate-800 shadow-sm outline-none transition-all focus:border-violet-500 focus:ring-2 focus:ring-violet-500/20"
            />
          </div>
        </div>
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
