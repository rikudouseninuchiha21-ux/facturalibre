"use client";

import { useState } from "react";
import { Pencil, Plus } from "lucide-react";

import { ContactForm } from "@/components/contacts/ContactForm";
import { Modal } from "@/components/ui/modal";
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
  const [creating, setCreating] = useState(false);
  const [editing, setEditing] = useState<Contact | null>(null);

  return (
    <>
      <Card>
        <CardHeader className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <CardTitle>Listado</CardTitle>
            <CardDescription>
              {contacts.length} contacto
              {contacts.length === 1 ? "" : "s"} encontrado
              {contacts.length === 1 ? "" : "s"}.
            </CardDescription>
          </div>
          <button
            type="button"
            onClick={() => setCreating(true)}
            className="inline-flex items-center justify-center gap-2 rounded-lg bg-violet-600 px-4 py-2 text-sm font-semibold text-white shadow-sm transition-colors hover:bg-violet-500"
          >
            <Plus className="size-4" aria-hidden="true" />
            Nuevo Contacto
          </button>
        </CardHeader>
        <CardContent>
          {contacts.length === 0 ? (
            <div className="rounded-xl border border-dashed border-slate-300 bg-slate-50 px-6 py-10 text-center">
              <p className="font-medium text-slate-700">
                Todavía no hay contactos
              </p>
              <p className="mt-1 text-sm text-slate-500">
                Usa el botón “Nuevo Contacto” para crear el primero.
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
                        className="inline-flex items-center gap-1.5 rounded-md px-2 py-1 text-xs font-semibold text-violet-700 transition-colors hover:bg-violet-50 hover:text-violet-900"
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

      {creating ? (
        <Modal
          title="Nuevo contacto"
          description="Registra un cliente o proveedor con sus datos fiscales DIAN."
          onClose={() => setCreating(false)}
          maxWidthClassName="max-w-2xl"
        >
          <ContactForm onSaved={() => setCreating(false)} />
        </Modal>
      ) : null}

      {editing ? (
        <Modal
          title="Editar contacto"
          description={`Actualiza los datos fiscales DIAN de ${editing.name}.`}
          onClose={() => setEditing(null)}
          maxWidthClassName="max-w-2xl"
        >
          <ContactForm
            contact={editing}
            onSaved={() => setEditing(null)}
            onCancel={() => setEditing(null)}
          />
        </Modal>
      ) : null}
    </>
  );
}
