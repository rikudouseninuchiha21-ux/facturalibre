import type { Metadata } from "next";

import { ContactForm } from "@/components/contacts/ContactForm";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
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
          Clientes y proveedores activos registrados en FacturaLibre.
        </p>
      </header>

      <Card>
        <CardHeader>
          <CardTitle>Nuevo Contacto</CardTitle>
          <CardDescription>
            Registra un cliente o proveedor. El nombre es obligatorio.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <ContactForm />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Listado</CardTitle>
          <CardDescription>
            {error
              ? "No fue posible obtener los datos."
              : `${contacts.length} contacto${contacts.length === 1 ? "" : "s"} encontrado${contacts.length === 1 ? "" : "s"}.`}
          </CardDescription>
        </CardHeader>
        <CardContent>
          {error ? (
            <div
              role="alert"
              className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700"
            >
              {error}
            </div>
          ) : contacts.length === 0 ? (
            <div className="rounded-xl border border-dashed border-slate-300 bg-slate-50 px-6 py-10 text-center">
              <p className="font-medium text-slate-700">
                Todavía no hay contactos
              </p>
              <p className="mt-1 text-sm text-slate-500">
                Usa el formulario de arriba para crear el primer contacto.
              </p>
            </div>
          ) : (
            <Table>
              <caption className="sr-only">Listado de contactos</caption>
              <TableHeader>
                <TableRow>
                  <TableHead>Nombre</TableHead>
                  <TableHead>Email</TableHead>
                  <TableHead>NIT / Tax ID</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {contacts.map((contact) => (
                  <TableRow key={contact.id}>
                    <TableCell className="font-medium text-slate-950">
                      {contact.name}
                    </TableCell>
                    <TableCell>{contact.email ?? "—"}</TableCell>
                    <TableCell className="font-mono text-xs">
                      {contact.tax_id ?? "—"}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
