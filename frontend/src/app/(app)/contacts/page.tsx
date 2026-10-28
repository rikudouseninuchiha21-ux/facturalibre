import type { Metadata } from "next";

import { ContactsClient } from "@/components/contacts/ContactsClient";
import { getContacts, type Contact } from "@/lib/api";
import { getSessionCookieHeader } from "@/lib/server-auth";

export const dynamic = "force-dynamic";

export const metadata: Metadata = {
  title: "Contactos",
};

export default async function ContactsPage() {
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
          Contactos
        </h1>
        <p className="mt-2 max-w-2xl text-slate-600">
          Clientes y proveedores activos registrados en VANTAGE, con sus
          datos fiscales DIAN para la factura electrónica.
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
        <ContactsClient contacts={contacts} />
      )}
    </div>
  );
}
