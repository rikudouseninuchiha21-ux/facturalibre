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

async function apiGet<T>(path: string): Promise<T> {
  const response = await fetch(`${getBaseUrl()}${API_PREFIX}${path}`, {
    headers: { Accept: "application/json" },
    cache: "no-store",
  });

  if (!response.ok) {
    let detail = `${response.status} ${response.statusText}`.trim();

    try {
      const body = (await response.json()) as { detail?: unknown };
      if (typeof body.detail === "string") {
        detail = body.detail;
      }
    } catch {
      // La respuesta de error no era JSON; se conserva el mensaje HTTP.
    }

    throw new ApiError(
      `Error al consultar ${path}: ${detail}`,
      response.status,
    );
  }

  return (await response.json()) as T;
}

export function getContacts(): Promise<Contact[]> {
  return apiGet<Contact[]>("/contacts");
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
