/**
 * Cliente HTTP tipado para la API v1 de FacturaLibre.
 *
 * En el navegador se usa una ruta relativa (`/api/v1/...`) para pasar por el
 * rewrite same-origin de Next.js y evitar CORS.
 *
 * En Server Components no existe un origen para una URL relativa, así que se
 * llama directamente al backend. `BACKEND_INTERNAL_URL` permite usar
 * `http://backend:8000` dentro de Docker Compose.
 */

const API_PREFIX = "/api/v1";

export type LifecycleStatus = "draft" | "issued" | "void";

export type PaymentStatus = "unpaid" | "partially_paid" | "paid" | "overpaid";

export interface Contact {
  id: string;
  name: string;
  email: string | null;
  tax_id: string | null;
  version: number;
  created_at: string;
  updated_at: string;
}

export interface ContactCreateInput {
  name: string;
  email?: string;
  tax_id?: string;
}

export interface VoidInvoiceInput {
  reason: string;
}

export interface Item {
  id: string;
  name: string;
  description: string | null;
  unit_price: string;
  tax_id: string | null;
  version: number;
  created_at: string;
  updated_at: string;
}

export interface Tax {
  id: string;
  name: string;
  rate: string;
  version: number;
  created_at: string;
  updated_at: string;
}

export interface InvoiceLine {
  id: string;
  item_id: string | null;
  description: string;
  quantity: string;
  unit_price: string;
  discount_percent: string;
  tax_rate: string;
  line_subtotal: string;
  line_tax: string;
  line_total: string;
}

export interface Invoice {
  id: string;
  number: string | null;
  contact_id: string;
  issue_date: string;
  due_date: string;
  currency: string;
  lifecycle_status: LifecycleStatus;
  payment_status: PaymentStatus;
  voided_reason: string | null;
  voided_at: string | null;
  subtotal: string;
  tax_total: string;
  total: string;
  balance: string;
  version: number;
  created_at: string;
  updated_at: string;
  lines: InvoiceLine[];
}

export class ApiError extends Error {
  readonly status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

function getBaseUrl(): string {
  if (typeof window !== "undefined") {
    return "";
  }

  return (process.env.BACKEND_INTERNAL_URL ?? "http://127.0.0.1:8000").replace(
    /\/$/,
    "",
  );
}

function formatErrorDetail(detail: unknown): string | null {
  if (typeof detail === "string") {
    return detail;
  }

  if (Array.isArray(detail)) {
    const messages = detail.map((entry) => {
      if (typeof entry !== "object" || entry === null) {
        return String(entry);
      }

      const item = entry as { loc?: unknown; msg?: unknown };
      const message =
        typeof item.msg === "string" ? item.msg : "Error de validación";

      if (!Array.isArray(item.loc)) {
        return message;
      }

      const location = item.loc
        .filter(
          (part): part is string | number =>
            typeof part === "string" || typeof part === "number",
        )
        .filter((part) => part !== "body")
        .join(".");

      return location ? `${location}: ${message}` : message;
    });

    return messages.join("; ");
  }

  if (detail !== undefined && detail !== null) {
    return JSON.stringify(detail) ?? String(detail);
  }

  return null;
}

async function getErrorDetail(
  response: Response,
  fallback: string,
): Promise<string> {
  try {
    const body = (await response.json()) as { detail?: unknown };
    return formatErrorDetail(body.detail) ?? fallback;
  } catch {
    // La respuesta de error no era JSON; se conserva el mensaje HTTP.
    return fallback;
  }
}

async function apiGet<T>(path: string): Promise<T> {
  const response = await fetch(`${getBaseUrl()}${API_PREFIX}${path}`, {
    headers: { Accept: "application/json" },
    cache: "no-store",
  });

  if (!response.ok) {
    const fallback = `${response.status} ${response.statusText}`.trim();
    const detail = await getErrorDetail(response, fallback);

    throw new ApiError(`Error al consultar ${path}: ${detail}`, response.status);
  }

  return (await response.json()) as T;
}

async function apiPost<T>(path: string, body?: unknown): Promise<T> {
  const response = await fetch(`${getBaseUrl()}${API_PREFIX}${path}`, {
    method: "POST",
    headers: {
      Accept: "application/json",
      ...(body === undefined ? {} : { "Content-Type": "application/json" }),
    },
    body: body === undefined ? undefined : JSON.stringify(body),
    cache: "no-store",
  });

  if (!response.ok) {
    const fallback = `${response.status} ${response.statusText}`.trim();
    const detail = await getErrorDetail(response, fallback);

    throw new ApiError(detail, response.status);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return (await response.json()) as T;
}

export function getContacts(): Promise<Contact[]> {
  return apiGet<Contact[]>("/contacts");
}

export function createContact(payload: ContactCreateInput): Promise<Contact> {
  return apiPost<Contact>("/contacts", payload);
}

export function getItems(): Promise<Item[]> {
  return apiGet<Item[]>("/items");
}

export function getTaxes(): Promise<Tax[]> {
  return apiGet<Tax[]>("/taxes");
}

export function getInvoices(): Promise<Invoice[]> {
  return apiGet<Invoice[]>("/invoices");
}

export function issueInvoice(invoiceId: string): Promise<Invoice> {
  return apiPost<Invoice>(`/invoices/${encodeURIComponent(invoiceId)}/issue`);
}

export function voidInvoice(
  invoiceId: string,
  payload: VoidInvoiceInput,
): Promise<Invoice> {
  return apiPost<Invoice>(
    `/invoices/${encodeURIComponent(invoiceId)}/void`,
    payload,
  );
}
