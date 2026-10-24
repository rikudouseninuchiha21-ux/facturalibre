import type { Metadata } from "next";

import { PurchaseForm } from "@/components/purchases/PurchaseForm";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
  getContacts,
  getItems,
  type Contact,
  type Item,
} from "@/lib/api";
import { getSessionCookieHeader } from "@/lib/server-auth";

export const dynamic = "force-dynamic";

export const metadata: Metadata = {
  title: "Nueva Compra",
};

function getTodayIsoDate(): string {
  const now = new Date();
  const year = now.getFullYear();
  const month = String(now.getMonth() + 1).padStart(2, "0");
  const day = String(now.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
};

function getPlusThirtyDaysIsoDate(): string {
  const now = new Date();
  now.setDate(now.getDate() + 30);
  const year = now.getFullYear();
  const month = String(now.getMonth() + 1).padStart(2, "0");
  const day = String(now.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
};

export default async function PurchaseNewPage() {
  const cookieHeader = await getSessionCookieHeader();

  let contacts: Contact[] = [];
  let items: Item[] = [];
  let error: string | null = null;

  try {
    [contacts, items] = await Promise.all([
      getContacts(cookieHeader),
      getItems(cookieHeader),
    ]);
  } catch (cause) {
    error =
      cause instanceof Error
        ? cause.message
        : "No se pudo cargar el catálogo para la compra.";
  }

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-3xl font-bold tracking-tight text-slate-950">
          Nueva Compra
        </h1>
        <p className="mt-2 max-w-2xl text-slate-600">
          Registra una factura de compra en borrador con sus líneas y costo
          unitario.
        </p>
      </header>

      {error ? (
        <div
          role="alert"
          className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700"
        >
          {error}
        </div>
      ) : (
        <Card>
          <CardHeader>
            <CardTitle>Datos de la compra</CardTitle>
            <CardDescription>
              Completa el proveedor, las fechas y las líneas de la factura de
              compra.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <PurchaseForm
              contacts={contacts}
              items={items}
              initialIssueDate={getTodayIsoDate()}
              initialDueDate={getPlusThirtyDaysIsoDate()}
            />
          </CardContent>
        </Card>
      )}
    </div>
  );
}
