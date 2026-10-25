import type { Metadata } from "next";

import { PosActions } from "@/components/pos/PosActions";
import { PosClient } from "@/components/pos/PosClient";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
  getContacts,
  type Contact,
} from "@/lib/api";
import { getSessionCookieHeader } from "@/lib/server-auth";

export const dynamic = "force-dynamic";

export const metadata: Metadata = {
  title: "Punto de Venta",
};

export default async function PosPage() {
  const cookieHeader = await getSessionCookieHeader();

  let contacts: Contact[] = [];
  let error: string | null = null;

  try {
    contacts = await getContacts(cookieHeader);
  } catch (cause) {
    error =
      cause instanceof Error
        ? cause.message
        : "No se pudo consultar el listado de contactos.";
  }

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-3xl font-bold tracking-tight text-slate-950">
          Punto de Venta
        </h1>
        <p className="mt-2 max-w-2xl text-slate-600">
          Venta rápida al mostrador. Busca productos, agrega al carrito y
          emite la factura al cobrar.
        </p>
      </header>

      {error ? (
        <Card>
          <CardHeader>
            <CardTitle>No se pudo abrir el punto de venta</CardTitle>
            <CardDescription>
              Revisa la conexión con el backend e inténtalo de nuevo.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div
              role="alert"
              className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700"
            >
              {error}
            </div>
            <PosActions />
          </CardContent>
        </Card>
      ) : (
        <PosClient contacts={contacts} />
      )}
    </div>
  );
}
