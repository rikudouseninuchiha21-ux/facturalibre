"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { BellOff, CircleAlert, Check, CheckCheck, Info, TriangleAlert } from "lucide-react";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  markAllNotificationsRead,
  markNotificationRead,
  type Notification,
  type NotificationSeverity,
} from "@/lib/api";
import { formatRelativeTime } from "@/lib/format";

const SEVERITY_ICON: Record<NotificationSeverity, typeof Info> = {
  INFO: Info,
  WARNING: TriangleAlert,
  CRITICAL: CircleAlert,
};

const SEVERITY_STYLES: Record<NotificationSeverity, { badge: string; ring: string }> = {
  INFO: {
    badge: "bg-zinc-100 text-zinc-600",
    ring: "ring-zinc-200",
  },
  WARNING: {
    badge: "bg-amber-100 text-amber-800",
    ring: "ring-amber-300",
  },
  CRITICAL: {
    badge: "bg-red-100 text-red-700",
    ring: "ring-red-300",
  },
};

const SEVERITY_LABEL: Record<NotificationSeverity, string> = {
  INFO: "Info",
  WARNING: "Atención",
  CRITICAL: "Crítico",
};

interface NotificationsClientProps {
  initialNotifications: Notification[];
  filter: "all" | "unread";
  page: number;
  pageSize: number;
}

export function NotificationsClient({
  initialNotifications,
  filter,
  page,
  pageSize,
}: NotificationsClientProps) {
  const router = useRouter();
  const [busyId, setBusyId] = useState<string | null>(null);
  const [markingAll, setMarkingAll] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const hasFullPage = initialNotifications.length === pageSize;
  const hasPrev = page > 1;

  function navigateWith(nextFilter: "all" | "unread", nextPage: number) {
    const params = new URLSearchParams({
      filter: nextFilter,
      page: String(nextPage),
    });
    router.push(`/notifications?${params.toString()}`);
  }

  async function handleMarkRead(notification: Notification) {
    setBusyId(notification.id);
    setError(null);
    try {
      await markNotificationRead(notification.id);
      router.refresh();
    } catch {
      setError("No se pudo marcar la notificación como leída.");
    } finally {
      setBusyId(null);
    }
  }

  async function handleMarkAllRead() {
    setMarkingAll(true);
    setError(null);
    try {
      await markAllNotificationsRead();
      router.refresh();
    } catch {
      setError("No se pudo marcar las notificaciones como leídas.");
    } finally {
      setMarkingAll(false);
    }
  }

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0">
        <div>
          <CardTitle>Bandeja</CardTitle>
          <CardDescription>
            {filter === "unread"
              ? "Solo notificaciones sin leer."
              : "Todas tus notificaciones, las más recientes primero."}
          </CardDescription>
        </div>
        <button
          type="button"
          onClick={() => void handleMarkAllRead()}
          disabled={markingAll}
          className="inline-flex items-center gap-2 rounded-lg border border-zinc-300 bg-white px-3 py-1.5 text-xs font-semibold text-zinc-700 shadow-sm transition-colors hover:border-violet-500 hover:text-violet-700 disabled:cursor-not-allowed disabled:opacity-50"
        >
          <CheckCheck className="size-4" aria-hidden="true" />
          {markingAll ? "Marcando…" : "Marcar todas como leídas"}
        </button>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex items-center gap-2">
          {(["all", "unread"] as const).map((option) => (
            <button
              key={option}
              type="button"
              onClick={() => navigateWith(option, 1)}
              className={`rounded-lg px-3 py-1.5 text-sm font-semibold transition-colors ${
                filter === option
                  ? "bg-violet-600 text-white"
                  : "border border-zinc-300 bg-white text-zinc-600 hover:bg-zinc-50"
              }`}
            >
              {option === "all" ? "Todas" : "No leídas"}
            </button>
          ))}
        </div>

        {error ? (
          <div
            role="alert"
            className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700"
          >
            {error}
          </div>
        ) : null}

        {initialNotifications.length === 0 ? (
          <div className="rounded-xl border border-dashed border-slate-300 bg-slate-50 px-6 py-12 text-center">
            <BellOff
              className="mx-auto size-8 text-zinc-400"
              aria-hidden="true"
            />
            <p className="mt-3 font-medium text-slate-700">
              No tienes notificaciones
            </p>
            <p className="mt-1 text-sm text-slate-500">
              Las alertas de presupuestos y los cierres aparecerán aquí.
            </p>
          </div>
        ) : (
          <ul className="divide-y divide-zinc-100">
            {initialNotifications.map((notification) => {
              const Icon = SEVERITY_ICON[notification.severity];
              const styles = SEVERITY_STYLES[notification.severity];
              const content = (
                <>
                  <span
                    className={`flex size-9 shrink-0 items-center justify-center rounded-full ring-1 ring-inset ${styles.badge} ${styles.ring}`}
                  >
                    <Icon className="size-4" aria-hidden="true" />
                  </span>
                  <span className="min-w-0 flex-1">
                    <span className="flex flex-wrap items-center gap-2">
                      <span className="text-sm font-semibold text-zinc-900">
                        {notification.title}
                      </span>
                      <span
                        className={`inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide ${styles.badge}`}
                      >
                        {SEVERITY_LABEL[notification.severity]}
                      </span>
                    </span>
                    {notification.body ? (
                      <span className="mt-0.5 block text-sm text-zinc-600">
                        {notification.body}
                      </span>
                    ) : null}
                    <span className="mt-0.5 block text-xs text-zinc-400">
                      {formatRelativeTime(notification.created_at)}
                      {notification.read_at ? " · Leída" : ""}
                    </span>
                  </span>
                </>
              );

              return (
                <li key={notification.id} className="flex items-start gap-3 py-3">
                  {notification.link ? (
                    <Link
                      href={notification.link}
                      className="flex w-full items-start gap-3 rounded-lg transition-colors hover:bg-violet-50/60"
                    >
                      {content}
                    </Link>
                  ) : (
                    <div className="flex w-full items-start gap-3">{content}</div>
                  )}
                  {!notification.read_at ? (
                    <button
                      type="button"
                      onClick={() => void handleMarkRead(notification)}
                      disabled={busyId === notification.id}
                      title="Marcar como leída"
                      aria-label={`Marcar como leída: ${notification.title}`}
                      className="shrink-0 rounded-lg border border-zinc-300 bg-white p-1.5 text-zinc-500 shadow-sm transition-colors hover:border-violet-500 hover:text-violet-700 disabled:cursor-not-allowed disabled:opacity-50"
                    >
                      <Check className="size-4" aria-hidden="true" />
                    </button>
                  ) : null}
                </li>
              );
            })}
          </ul>
        )}

        {(hasPrev || hasFullPage) && initialNotifications.length > 0 ? (
          <div className="flex items-center justify-between border-t border-zinc-100 pt-4">
            <button
              type="button"
              onClick={() => navigateWith(filter, page - 1)}
              disabled={!hasPrev}
              className="rounded-lg border border-zinc-300 bg-white px-3 py-1.5 text-sm font-semibold text-zinc-700 shadow-sm transition-colors hover:bg-zinc-50 disabled:cursor-not-allowed disabled:opacity-40"
            >
              Anterior
            </button>
            <span className="text-sm text-zinc-500">Página {page}</span>
            <button
              type="button"
              onClick={() => navigateWith(filter, page + 1)}
              disabled={!hasFullPage}
              className="rounded-lg border border-zinc-300 bg-white px-3 py-1.5 text-sm font-semibold text-zinc-700 shadow-sm transition-colors hover:bg-zinc-50 disabled:cursor-not-allowed disabled:opacity-40"
            >
              Siguiente
            </button>
          </div>
        ) : null}
      </CardContent>
    </Card>
  );
}
