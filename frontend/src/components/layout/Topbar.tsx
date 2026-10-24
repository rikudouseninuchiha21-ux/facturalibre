"use client";

import { LogOut, Search } from "lucide-react";

import { ThemeToggle } from "./ThemeToggle";

interface TopbarProps {
  currentUser: { full_name: string; role: string } | null;
}

export function Topbar({ currentUser }: TopbarProps) {
  return (
    <header className="sticky top-0 z-30 flex h-16 items-center justify-between px-6 py-2.5 bg-white/80 backdrop-blur-md border-b border-zinc-200 dark:bg-zinc-950/80 dark:border-zinc-800 shrink-0">
      <div className="flex items-center gap-4">
        <div className="hidden md:flex-1 max-w-md">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 size-4 text-zinc-400 -translate-y-1/2" />
            <input
              type="text"
              placeholder="Buscar..."
              className="w-full pl-10 pr-4 py-2 rounded-lg border border-zinc-200 bg-white text-sm text-zinc-900 shadow-sm outline-none transition-all focus:border-indigo-600 focus:ring-2 focus:ring-indigo-600/20 dark:border-zinc-800 dark:bg-zinc-800 dark:text-zinc-100 dark:focus:border-indigo-500 dark:focus:ring-indigo-500/30"
            />
          </div>
        </div>
      </div>

      <div className="flex items-center gap-3">
        <ThemeToggle />

        {currentUser && (
          <div className="flex items-center gap-3 pl-4 border-l border-zinc-200 dark:border-zinc-800 shrink-0">
            <div className="flex flex-col min-w-0">
              <span
                title={currentUser.full_name}
                className="max-w-[150px] truncate text-sm font-medium text-zinc-900 dark:text-zinc-100"
              >
                {currentUser.full_name}
              </span>
              <span
                className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded bg-zinc-100 text-zinc-600 dark:bg-zinc-800/30 dark:text-zinc-400"
              >
                {currentUser.role}
              </span>
            </div>
            <button
              type="button"
              className="p-2 rounded-md text-zinc-600 hover:bg-zinc-100 hover:text-zinc-900 dark:text-zinc-400 dark:hover:bg-zinc-800 dark:hover:text-white transition-colors"
              aria-label="Cerrar sesión"
            >
              <LogOut className="size-5" />
            </button>
          </div>
        )}
      </div>
    </header>
  );
}
