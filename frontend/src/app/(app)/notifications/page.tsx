import type { Metadata } from "next";

import { NotificationsClient } from "@/components/notifications/NotificationsClient";
import { getNotifications, type Notification } from "@/lib/api";
import { getSessionCookieHeader } from "@/lib/server-auth";

export const dynamic = "force-dynamic";

export const metadata: Metadata = {
  title: "Notificaciones",
};

const PAGE_SIZE = 20;

interface NotificationsPageProps {
  searchParams: Promise<{
    filter?: string;
    page?: string;
  }>;
}

export default async function NotificationsPage({
  searchParams,
}: NotificationsPageProps) {
  const cookieHeader = await getSessionCookieHeader();
  const params = await searchParams;
  const filter = params.filter === "unread" ? "unread" : "all";
  const page = Math.max(Number(params.page) || 1, 1);
  const offset = (page - 1) * PAGE_SIZE;

  let notifications: Notification[] = [];
  let error: string | null = null;

  try {
    const query = new URLSearchParams({
      limit: String(PAGE_SIZE),
      offset: String(offset),
    });
    if (filter === "unread") {
      query.set("unread_only", "true");
    }
    notifications = await getNotifications(query.toString(), cookieHeader);
  } catch (cause) {
    error =
      cause instanceof Error
        ? cause.message
        : "No se pudo consultar las notificaciones.";
  }

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-3xl font-bold tracking-tight text-slate-950">
          Notificaciones
        </h1>
        <p className="mt-2 max-w-2xl text-slate-600">
          Alertas de presupuesto, aprobaciones y cierres automáticos del
          sistema.
        </p>
      </header>

      {error ? (
        <div
          role="alert"
          className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700"
        >
          {error}
        </div>
      ) : null}

      <NotificationsClient
        initialNotifications={notifications}
        filter={filter}
        page={page}
        pageSize={PAGE_SIZE}
      />
    </div>
  );
}
