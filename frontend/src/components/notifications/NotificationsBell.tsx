"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { Bell, BellOff, CircleAlert, Info, TriangleAlert } from "lucide-react";

import {
  getNotifications,
  getUnreadNotificationCount,
  markAllNotificationsRead,
  type Notification,
  type NotificationSeverity,
} from "@/lib/api";
import { formatRelativeTime } from "@/lib/format";

const POLL_INTERVAL_MS = 30_000;
const DROPDOWN_ITEMS = 5;

const SEVERITY_ICON: Record<NotificationSeverity, typeof Info> = {
  INFO: Info,
  WARNING: TriangleAlert,
  CRITICAL: CircleAlert,
};

const SEVERITY_STYLES: Record<NotificationSeverity, string> = {
  INFO: "bg-zinc-100 text-zinc-600",
  WARNING: "bg-amber-100 text-amber-700",
  CRITICAL: "bg-red-100 text-red-700",
};

export function NotificationsBell() {
  const router = useRouter();
  const [count, setCount] = useState(0);
  const [isOpen, setIsOpen] = useState(false);
  const [latest, setLatest] = useState<Notification[]>([]);
  const containerRef = useRef<HTMLDivElement | null>(null);

  // Único punto de polling de la app: la campana consulta el contador de no
  // leídas cada 30 segundos. El estado se actualiza en los callbacks de las
  // promesas, nunca de forma síncrona dentro del efecto.
  useEffect(() => {
    let cancelled = false;
    const fetchCount = () => {
      getUnreadNotificationCount()
        .then(({ count: unread }) => {
          if (!cancelled) setCount(unread);
        })
        .catch(() => {
          // Sin sesión válida o error de red: el badge queda como está.
        });
    };

    fetchCount();
    const interval = setInterval(fetchCount, POLL_INTERVAL_MS);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, []);

  // Al abrir el dropdown se cargan las últimas no leídas (máximo 5).
  useEffect(() => {
    if (!isOpen) return;
    let cancelled = false;
    getNotifications("unread_only=true&limit=5")
      .then((items) => {
        if (!cancelled) setLatest(items.slice(0, DROPDOWN_ITEMS));
      })
      .catch(() => {
        if (!cancelled) setLatest([]);
      });
    getUnreadNotificationCount()
      .then(({ count: unread }) => {
        if (!cancelled) setCount(unread);
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, [isOpen]);

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (
        containerRef.current &&
        !containerRef.current.contains(event.target as Node)
      ) {
        setIsOpen(false);
      }
    }
    if (isOpen) {
      document.addEventListener("mousedown", handleClickOutside);
    }
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [isOpen]);

  async function handleMarkAllRead() {
    try {
      await markAllNotificationsRead();
      const [unreadResult, items] = await Promise.all([
        getUnreadNotificationCount(),
        getNotifications("unread_only=true&limit=5"),
      ]);
      setCount(unreadResult.count);
      setLatest(items.slice(0, DROPDOWN_ITEMS));
      router.refresh();
    } catch {
      // El usuario puede reintentar desde la página de notificaciones.
    }
  }

  const badgeLabel = count > 99 ? "99+" : String(count);

  return (
    <div ref={containerRef} className="relative">
      <button
        type="button"
        onClick={() => setIsOpen((open) => !open)}
        aria-label={`Notificaciones: ${count} sin leer`}
        aria-expanded={isOpen}
        className="relative rounded-lg p-2 text-zinc-500 transition-colors hover:bg-zinc-100 hover:text-amber-700"
      >
        <Bell className="size-5" aria-hidden="true" />
        {count > 0 ? (
          <span
            aria-hidden="true"
            className="absolute -right-0.5 -top-0.5 flex min-w-[18px] items-center justify-center rounded-full bg-gradient-to-br from-amber-400 to-amber-600 px-1 text-[10px] font-bold text-zinc-950 shadow"
          >
            {badgeLabel}
          </span>
        ) : null}
      </button>

      {isOpen ? (
        <div
          role="dialog"
          aria-label="Notificaciones recientes"
          className="absolute right-0 top-full z-50 mt-2 w-80 overflow-hidden rounded-xl border border-zinc-200 bg-white shadow-xl"
        >
          <div className="flex items-center justify-between border-b border-zinc-100 px-4 py-3">
            <p className="text-sm font-semibold text-zinc-900">Notificaciones</p>
            {count > 0 ? (
              <button
                type="button"
                onClick={() => void handleMarkAllRead()}
                className="text-xs font-semibold text-amber-700 hover:text-amber-800"
              >
                Marcar todas
              </button>
            ) : null}
          </div>

          <div className="max-h-80 overflow-y-auto">
            {latest.length === 0 ? (
              <div className="flex items-center gap-3 px-4 py-6 text-sm text-zinc-500">
                <BellOff className="size-5 shrink-0 text-zinc-400" aria-hidden="true" />
                No tienes notificaciones sin leer
              </div>
            ) : (
              <ul className="divide-y divide-zinc-100">
                {latest.map((notification) => {
                  const Icon = SEVERITY_ICON[notification.severity];
                  return (
                    <li key={notification.id}>
                      <Link
                        href={notification.link ?? "/notifications"}
                        onClick={() => setIsOpen(false)}
                        className="flex items-start gap-3 px-4 py-3 transition-colors hover:bg-amber-50/60"
                      >
                        <span
                          className={`mt-0.5 flex size-7 shrink-0 items-center justify-center rounded-full ${SEVERITY_STYLES[notification.severity]}`}
                        >
                          <Icon className="size-4" aria-hidden="true" />
                        </span>
                        <span className="min-w-0">
                          <span className="block truncate text-sm font-medium text-zinc-900">
                            {notification.title}
                          </span>
                          <span className="block text-xs text-zinc-500">
                            {formatRelativeTime(notification.created_at)}
                          </span>
                        </span>
                      </Link>
                    </li>
                  );
                })}
              </ul>
            )}
          </div>

          <div className="border-t border-zinc-100">
            <Link
              href="/notifications"
              onClick={() => setIsOpen(false)}
              className="block px-4 py-2.5 text-center text-sm font-semibold text-amber-700 transition-colors hover:bg-amber-50"
            >
              Ver todas
            </Link>
          </div>
        </div>
      ) : null}
    </div>
  );
}
