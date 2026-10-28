import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { ArrowLeft } from "lucide-react";

import {
  CustomerAccountClient,
  type InvoiceOption,
} from "@/components/receivables/CustomerAccountClient";
import {
  ApiError,
  getAgreements,
  getContact,
  getCurrentUser,
  getCustomerAging,
  getCustomerStatement,
  getInvoices,
  getReminders,
  type Contact,
  type CustomerAging,
  type CustomerStatement,
  type PaymentAgreement,
  type PaymentReminder,
} from "@/lib/api";
import { getSessionCookieHeader } from "@/lib/server-auth";

export const dynamic = "force-dynamic";

export async function generateMetadata({
  params,
}: {
  params: Promise<{ contact_id: string }>;
}): Promise<Metadata> {
  const { contact_id } = await params;
  const cookieHeader = await getSessionCookieHeader();
  try {
    const contact = await getContact(contact_id, cookieHeader);
    return { title: `Cartera ${contact.name}` };
  } catch {
    return { title: "Cartera" };
  }
}

function emptyAging(contactId: string, name: string): CustomerAging {
  return {
    contact_id: contactId,
    contact_name: name,
    current: "0.00",
    d0_30: "0.00",
    d31_60: "0.00",
    d61_90: "0.00",
    d91_120: "0.00",
    d120_plus: "0.00",
    total: "0.00",
    total_overdue: "0.00",
    invoice_count: 0,
  };
}

export default async function CustomerAccountPage({
  params,
}: {
  params: Promise<{ contact_id: string }>;
}) {
  const { contact_id } = await params;
  const cookieHeader = await getSessionCookieHeader();

  let contact: Contact;
  try {
    contact = await getContact(contact_id, cookieHeader);
  } catch (cause) {
    if (cause instanceof ApiError && cause.status === 404) {
      notFound();
    }
    throw cause;
  }

  const now = new Date();
  const fromDate = `${now.getFullYear()}-01-01`;
  const toDate = now.toISOString().slice(0, 10);

  const [agingResult, statementResult, remindersResult, agreementsResult, invoicesResult, userResult] =
    await Promise.allSettled([
      getCustomerAging(contact_id, undefined, cookieHeader),
      getCustomerStatement(contact_id, fromDate, toDate, cookieHeader),
      getReminders(`contact_id=${encodeURIComponent(contact_id)}&limit=50`, cookieHeader),
      getAgreements(`contact_id=${encodeURIComponent(contact_id)}`, cookieHeader),
      getInvoices(cookieHeader),
      getCurrentUser(cookieHeader),
    ]);

  const aging =
    agingResult.status === "fulfilled"
      ? agingResult.value
      : emptyAging(contact_id, contact.name);
  const statement: CustomerStatement =
    statementResult.status === "fulfilled"
      ? statementResult.value
      : {
          contact_id,
          contact_name: contact.name,
          from_date: fromDate,
          to_date: toDate,
          opening_balance: aging.total,
          lines: [],
          closing_balance: aging.total,
        };
  const reminders: PaymentReminder[] =
    remindersResult.status === "fulfilled" ? remindersResult.value : [];
  const agreements: PaymentAgreement[] =
    agreementsResult.status === "fulfilled" ? agreementsResult.value : [];
  const invoices: InvoiceOption[] =
    invoicesResult.status === "fulfilled"
      ? invoicesResult.value
          .filter(
            (invoice) =>
              invoice.contact_id === contact_id &&
              invoice.lifecycle_status === "issued" &&
              Number(invoice.balance) > 0,
          )
          .map((invoice) => ({
            id: invoice.id,
            number: invoice.number,
            issue_date: invoice.issue_date,
            due_date: invoice.due_date,
            balance: invoice.balance,
          }))
      : [];
  const canManage =
    userResult.status === "fulfilled" &&
    (userResult.value.role === "ADMIN" || userResult.value.role === "ACCOUNTANT");

  return (
    <div className="space-y-6">
      <header>
        <Link
          href="/receivables"
          className="inline-flex items-center gap-2 text-sm font-semibold text-violet-700 transition-colors hover:text-violet-900"
        >
          <ArrowLeft className="size-4" aria-hidden="true" />
          Volver a cartera
        </Link>
        <h1 className="mt-3 text-3xl font-bold tracking-tight text-slate-950">
          {contact.name}
        </h1>
        <p className="mt-2 max-w-2xl text-slate-600">
          Estado de cuenta, aging, recordatorios y acuerdos de pago del
          cliente.
        </p>
      </header>

      <CustomerAccountClient
        contactId={contact_id}
        contactName={contact.name}
        aging={aging}
        statement={statement}
        reminders={reminders}
        agreements={agreements}
        invoices={invoices}
        canManage={canManage}
      />
    </div>
  );
}
