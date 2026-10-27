"use client";

import { useState } from "react";
import { Pencil, X } from "lucide-react";

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
import type { Contact } from "@/lib/api";

const TAX_REGIME_LABELS: Record<string, string> = {
  RESPONSABLE_IVA: "Responsable de IVA",
  NO_RESPONSABLE: "No responsable",
  GRAN_CONTRIBUYENTE: "Gran contribuyente",
  AUTORRETENEDOR: "Autorretenedor",
  REGIMEN_SIMPLE: "Régimen simple",
};

interface ContactsClientProps {
  contacts: Contact[];
}

export function ContactsClient({ contacts }: ContactsClientProps) {
  const [editing, setEditing] = useState<Contact | null>(null);

  return (
    <>
      <Card>
        <CardHeader>
          <CardTitle>Nuevo Contacto</CardTitle>
          <CardDescription>
            Registra un cliente o proveedor con sus datos fiscales DIAN. El
            nombre es obligatorio.
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
            {contacts.length} contacto
            {contacts.length === 1 ? "" : "s"} encontrado
            {contacts.length === 1 ? "" : "s"}.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {contacts.length === 0 ? (
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
                  <TableHead>Dirección</TableHead>
                  <TableHead>Régimen</TableHead>
                  <TableHead className="text-right">Acciones</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {contacts.map((contact) => (
                  <TableRow key={contact.id}>
                    <TableCell className="max-w-52 truncate font-medium text-slate-950">
                      {contact.name}
                    </TableCell>
                    <TableCell className="max-w-44 truncate">
                      {contact.email ?? "—"}
                    </TableCell>
                    <TableCell className="whitespace-nowrap font-mono text-xs">
                      {contact.tax_id
                        ? `${contact.tax_id}${contact.dv ? `-${contact.dv}` : ""}`
                        : "—"}
                    </TableCell>
                    <TableCell className="max-w-52 truncate text-slate-600">
                      {contact.address ?? "—"}
                    </TableCell>
                    <TableCell className="text-slate-600">
                      {contact.tax_regime
                        ? (TAX_REGIME_LABELS[contact.tax_regime] ??
                          contact.tax_regime)
                        : "—"}
                    </TableCell>
                    <TableCell className="text-right">
                      <button
                        type="button"
                        onClick={() => setEditing(contact)}
                        className="inline-flex items-center gap-1.5 rounded-md px-2 py-1 text-xs font-semibold text-amber-700 transition-colors hover:bg-amber-50 hover:text-amber-900"
                      >
                        <Pencil className="size-3.5" aria-hidden="true" />
                        Editar
                      </button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {editing ? (
        <div className="fixed inset-0 z-[60] flex items-center justify-center bg-zinc-950/50 p-4">
          <div
            role="dialog"
            aria-modal="true"
            aria-label={`Editar contacto ${editing.name}`}
            className="max-h-[90vh] w-full max-w-2xl overflow-y-auto rounded-2xl border border-zinc-200 bg-white shadow-2xl"
          >
            <div className="flex items-start justify-between gap-4 border-b border-zinc-100 px-6 py-4">
              <div>
                <h2 className="text-lg font-semibold text-zinc-950">
                  Editar contacto
                </h2>
                <p className="mt-1 text-sm text-zinc-500">
                  Actualiza los datos fiscales DIAN de {editing.name}.
                </p>
              </div>
              <button
                type="button"
                onClick={() => setEditing(null)}
                aria-label="Cerrar"
                className="rounded-lg p-1.5 text-zinc-500 transition-colors hover:bg-zinc-100 hover:text-zinc-900"
              >
                <X className="size-5" aria-hidden="true" />
              </button>
            </div>
            <div className="px-6 py-5">
              <ContactForm
                contact={editing}
                onSaved={() => setEditing(null)}
                onCancel={() => setEditing(null)}
              />
            </div>
          </div>
        </div>
      ) : null}
    </>
  );
}
