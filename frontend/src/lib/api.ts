/**
 * Cliente HTTP tipado para la API v1 de VANTAGE.
 *
 * En el navegador se usa una ruta relativa (`/api/v1/...`) para pasar por el
 * rewrite same-origin de Next.js y evitar CORS.
 *
 * En Server Components no existe un origen para una URL relativa, así que se
 * llama directamente al backend. `BACKEND_INTERNAL_URL` permite usar
 * `http://backend:8000` dentro de Docker Compose.
 */

const API_PREFIX = "/api/v1";

export interface UserCompany {
  id: string;
  name: string;
  tax_id: string | null;
  role: string;
}

export interface User {
  id: string;
  email: string;
  full_name: string;
  role: string;
  is_active: boolean;
  created_at: string;
  active_company_id?: string | null;
  active_company_name?: string | null;
  companies?: UserCompany[];
}

export interface Company {
  id: string;
  name: string;
  tax_id: string | null;
  dv: string | null;
  address: string | null;
  phone: string | null;
  email: string | null;
  tax_regime: string | null;
  person_type: string | null;
  fiscal_responsibility: string | null;
  dian_municipality_code: string | null;
  dian_department_code: string | null;
  created_at: string;
  updated_at: string;
}

export interface CompanyMembership {
  company: Company;
  role: string;
}

export interface CompanyCreateInput {
  name: string;
  tax_id?: string;
  dv?: string;
  address?: string;
  phone?: string;
  email?: string;
  tax_regime?: string;
  person_type?: string;
  fiscal_responsibility?: string;
  dian_municipality_code?: string;
  dian_department_code?: string;
}

export interface CompanyUser {
  user_id: string;
  email: string;
  full_name: string;
  role: string;
  is_active: boolean;
}

export interface CompanyUserAssignInput {
  user_id: string;
  role: string;
}

export interface CrmStage {
  id: string;
  name: string;
  order: number;
  color: string;
  is_won: boolean;
  is_lost: boolean;
}

export interface CrmOpportunity {
  id: string;
  contact_id: string;
  contact_name: string;
  stage_id: string;
  stage_name: string;
  owner_id: string;
  owner_name: string;
  title: string;
  amount: string;
  expected_close_date: string | null;
  notes: string | null;
  quote_id: string | null;
  invoice_id: string | null;
  is_won: boolean;
  is_lost: boolean;
  created_at: string;
  updated_at: string;
}

export type CrmActivityType = "CALL" | "EMAIL" | "MEETING" | "NOTE";

export interface CrmActivity {
  id: string;
  opportunity_id: string;
  type: CrmActivityType;
  description: string;
  activity_date: string;
  created_by: string;
  created_by_name: string;
  created_at: string;
}

export interface CrmOpportunityDetail extends CrmOpportunity {
  activities: CrmActivity[];
}

export interface CrmOpportunityCreateInput {
  contact_id: string;
  stage_id: string;
  owner_id?: string;
  title: string;
  amount: string;
  expected_close_date?: string;
  notes?: string;
}

export interface CrmActivityCreateInput {
  type: CrmActivityType;
  description: string;
  activity_date?: string;
}

export interface LoginInput {
  email: string;
  password: string;
}

export interface RegisterInput extends LoginInput {
  full_name: string;
}

export type LifecycleStatus = "draft" | "issued" | "void";

export type PaymentStatus = "unpaid" | "partially_paid" | "paid" | "overpaid";

export type DianDocumentStatus =
  | "BORRADOR"
  | "GENERADO"
  | "GENERADO_SIN_PIN"
  | "ENVIADO"
  | "ACEPTADO"
  | "RECHAZADO";

export interface Contact {
  id: string;
  name: string;
  email: string | null;
  tax_id: string | null;
  type: string;
  status: string;
  version: number;
  // Datos fiscales DIAN (Fase 38A).
  dv: string | null;
  tax_regime: string | null;
  person_type: string | null;
  fiscal_responsibility: string | null;
  dian_municipality_code: string | null;
  dian_department_code: string | null;
  country_code: string;
  address: string | null;
  created_at: string;
  updated_at: string;
}

export interface ContactCreateInput {
  name: string;
  email?: string;
  tax_id?: string;
  type?: string;
  status?: string;
  address?: string;
  dv?: string;
  tax_regime?: string;
  person_type?: string;
  fiscal_responsibility?: string;
  dian_municipality_code?: string;
  dian_department_code?: string;
}

export interface ContactUpdateInput {
  name?: string;
  email?: string;
  tax_id?: string;
  type?: string;
  status?: string;
  address?: string;
  dv?: string;
  tax_regime?: string;
  person_type?: string;
  fiscal_responsibility?: string;
  dian_municipality_code?: string;
  dian_department_code?: string;
  version: number;
}

export interface VoidInvoiceInput {
  reason: string;
}

export type PurchaseStatus = "draft" | "issued" | "void";

export interface PurchaseLineInput {
  item_id?: string;
  description: string;
  quantity: string;
  unit_cost: string;
  tax_rate: string;
}

export interface PurchaseCreateInput {
  supplier_id: string;
  issue_date: string;
  due_date: string;
  lines: PurchaseLineInput[];
}

export interface PurchaseLine {
  id: string;
  item_id: string | null;
  description: string;
  quantity: string;
  unit_cost: string;
  tax_rate: string;
  line_subtotal: string;
  line_tax: string;
  line_total: string;
}

export interface Purchase {
  id: string;
  number: string | null;
  supplier_id: string;
  supplier: Contact;
  issue_date: string;
  due_date: string;
  status: PurchaseStatus;
  subtotal: string;
  tax_total: string;
  total: string;
  balance: string;
  version: number;
  created_at: string;
  updated_at: string;
  lines: PurchaseLine[];
}

export interface InvoiceLineInput {
  item_id: string;
  description?: string;
  quantity: string;
  unit_price: string;
  discount_percent: string;
  tax_rate: string;
}

export interface InvoiceCreateInput {
  contact_id: string;
  issue_date: string;
  due_date: string;
  currency: "COP";
  /** Catálogo DIAN: 10, 20, 42, 48, 49 o ZZZ. */
  payment_mean_code?: string;
  lines: InvoiceLineInput[];
}

export interface Item {
  id: string;
  name: string;
  description: string | null;
  unit_price: string;
  tax_id: string | null;
  price_includes_tax: boolean;
  version: number;
  created_at: string;
  updated_at: string;
}

export interface ItemCreateInput {
  name: string;
  description?: string;
  unit_price: string;
  tax_id?: string;
  price_includes_tax?: boolean;
}

export interface Tax {
  id: string;
  name: string;
  rate: string;
  version: number;
  created_at: string;
  updated_at: string;
}

export interface TaxCreateInput {
  name: string;
  rate: string;
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
  contact: Contact;
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
  payment_mean_code: string | null;
  cufe: string | null;
  dian_status: DianDocumentStatus | null;
  version: number;
  created_at: string;
  updated_at: string;
  lines: InvoiceLine[];
}

export interface Payment {
  id: string;
  invoice_id: string;
  amount: string;
  payment_date: string;
  method: string;
  reference: string | null;
  bank_movement_id: string | null;
  created_at: string;
}

export interface PaymentCreateInput {
  amount: string;
  payment_date: string;
  method: string;
  reference?: string;
}

export interface InvoiceStatusSummary {
  draft: number;
  issued: number;
  void: number;
}

export interface MonthlySalesPoint {
  month: string;
  total: string;
}

export interface DashboardSummary {
  total_revenue: string;
  total_invoiced: string;
  pending_balance: string;
  invoices_by_status: InvoiceStatusSummary;
  monthly_sales: MonthlySalesPoint[];
}

export interface Warehouse {
  id: string;
  name: string;
  code: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface WarehouseCreateInput {
  name: string;
  code: string;
}

export interface Expense {
  id: string;
  date: string;
  concept: string;
  amount: string;
  payment_method: string;
  reference: string | null;
  bank_movement_id: string | null;
  version: number;
  created_at: string;
  updated_at: string;
}

export interface ExpenseCreateInput {
  date: string;
  concept: string;
  amount: string;
  payment_method: string;
  reference?: string;
  cost_center_id?: string;
}

export type FixedAssetStatus = "ACTIVE" | "DISPOSED";

export interface FixedAsset {
  id: string;
  code: string;
  name: string;
  purchase_date: string;
  initial_cost: string;
  salvage_value: string;
  useful_life_months: number;
  status: FixedAssetStatus;
  monthly_depreciation: string;
  accumulated_depreciation: string;
  current_value: string;
  is_fully_depreciated: boolean;
  created_at: string;
}

export interface FixedAssetCreateInput {
  code: string;
  name: string;
  purchase_date: string;
  initial_cost: string;
  salvage_value: string;
  useful_life_months: number;
}

export interface DepreciateAssetInput {
  month: number;
  year: number;
}

export type StockMovementType = "IN" | "OUT";

export interface StockBalance {
  item_id: string;
  item_name: string;
  warehouse_id: string;
  warehouse_name: string;
  quantity: string;
  updated_at: string;
}

export interface StockMovementInput {
  item_id: string;
  warehouse_id: string;
  movement_type: StockMovementType;
  quantity: string;
  unit_cost?: string;
  reference?: string;
}

export interface StockMovement {
  id: string;
  item_id: string;
  warehouse_id: string;
  movement_type: StockMovementType;
  quantity: string;
  unit_cost: string | null;
  reference: string | null;
  created_at: string;
}

export interface Employee {
  id: string;
  document: string;
  first_name: string;
  last_name: string;
  email: string | null;
  base_salary: string;
  start_date: string;
  is_active: boolean;
  created_at: string;
}

export interface EmployeeCreateInput {
  document: string;
  first_name: string;
  last_name: string;
  email?: string;
  base_salary: string;
  start_date: string;
  is_active?: boolean;
  document_type?: string;
  address?: string;
  municipality_code?: string;
  department_code?: string;
  contract_type?: string;
  salary_type?: string;
  risk_level?: string;
  eps_code?: string;
  afp_code?: string;
  arl_code?: string;
  severance_fund_code?: string;
  compensation_fund_code?: string;
}

export type PayrollPeriodStatus = "DRAFT" | "CLOSED";

export interface PayrollDetail {
  id: string;
  period_id: string;
  employee_id: string;
  employee_name: string;
  employee_document: string;
  base_salary: string;
  health_deduction: string;
  pension_deduction: string;
  net_pay: string;
  created_at: string;
}

export interface PayrollPeriod {
  id: string;
  month: number;
  year: number;
  status: PayrollPeriodStatus;
  dian_cune: string | null;
  dian_status: DianDocumentStatus | null;
  payment_date: string | null;
  created_at: string;
  details: PayrollDetail[];
  total_base: string;
  total_health: string;
  total_pension: string;
  total_net: string;
}

export interface PayrollPeriodCreateInput {
  month: number;
  year: number;
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

async function apiGet<T>(path: string, cookieHeader?: string): Promise<T> {
  const headers: Record<string, string> = { Accept: "application/json" };
  if (cookieHeader) {
    // En Server Components no existe un cookie jar: se reenvía la cookie
    // recibida por Next.js para que el backend autentique la petición.
    headers.Cookie = cookieHeader;
  }

  const response = await fetch(`${getBaseUrl()}${API_PREFIX}${path}`, {
    headers,
    credentials: "include",
    cache: "no-store",
  });

  if (!response.ok) {
    const fallback = `${response.status} ${response.statusText}`.trim();
    const detail = await getErrorDetail(response, fallback);

    throw new ApiError(`Error al consultar ${path}: ${detail}`, response.status);
  }

  return (await response.json()) as T;
}

interface ApiPostOptions {
  headers?: Record<string, string>;
}

async function apiDelete<T>(path: string): Promise<T> {
  const response = await fetch(`${getBaseUrl()}${API_PREFIX}${path}`, {
    method: "DELETE",
    headers: { Accept: "application/json" },
    credentials: "include",
    cache: "no-store",
  });

  if (!response.ok) {
    const fallback = `${response.status} ${response.statusText}`.trim();
    const detail = await getErrorDetail(response, fallback);
    throw new ApiError(`Error al eliminar ${path}: ${detail}`, response.status);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return (await response.json()) as T;
}

async function apiPatch<T>(
  path: string,
  body?: unknown,
  cookieHeader?: string,
): Promise<T> {
  const headers: Record<string, string> = { Accept: "application/json" };
  if (cookieHeader) {
    headers.Cookie = cookieHeader;
  }
  headers["Content-Type"] = "application/json";

  const response = await fetch(`${getBaseUrl()}${API_PREFIX}${path}`, {
    method: "PATCH",
    headers,
    body: JSON.stringify(body),
    credentials: "include",
    cache: "no-store",
  });

  if (!response.ok) {
    const fallback = `${response.status} ${response.statusText}`.trim();
    const detail = await getErrorDetail(response, fallback);
    throw new ApiError(`Error al actualizar ${path}: ${detail}`, response.status);
  }

  return (await response.json()) as T;
}
async function apiPut<T>(
  path: string,
  body?: unknown,
  cookieHeader?: string,
): Promise<T> {
  const headers: Record<string, string> = { Accept: "application/json" };
  if (cookieHeader) {
    headers.Cookie = cookieHeader;
  }
  headers["Content-Type"] = "application/json";

  const response = await fetch(`${getBaseUrl()}${API_PREFIX}${path}`, {
    method: "PUT",
    headers,
    body: JSON.stringify(body),
    credentials: "include",
    cache: "no-store",
  });

  if (!response.ok) {
    const fallback = `${response.status} ${response.statusText}`.trim();
    const detail = await getErrorDetail(response, fallback);
    throw new ApiError(`Error al actualizar ${path}: ${detail}`, response.status);
  }

  return (await response.json()) as T;
}

async function apiPost<T>(
  path: string,
  body?: unknown,
  options?: ApiPostOptions,
  cookieHeader?: string,
): Promise<T> {
  const headers: Record<string, string> = {
    Accept: "application/json",
    ...options?.headers,
  };
  if (cookieHeader) {
    headers.Cookie = cookieHeader;
  }
  if (body !== undefined) {
    headers["Content-Type"] = "application/json";
  }

  const response = await fetch(`${getBaseUrl()}${API_PREFIX}${path}`, {
    method: "POST",
    headers,
    body: body === undefined ? undefined : JSON.stringify(body),
    credentials: "include",
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
export function getContacts(cookieHeader?: string): Promise<Contact[]> {
  return apiGet<Contact[]>("/contacts", cookieHeader);
}

export function createContact(payload: ContactCreateInput): Promise<Contact> {
  return apiPost<Contact>("/contacts", payload);
}

export function updateContact(
  id: string,
  payload: ContactUpdateInput,
): Promise<Contact> {
  return apiPatch<Contact>(
    `/contacts/${encodeURIComponent(id)}`,
    payload,
  );
}

export function getItems(cookieHeader?: string): Promise<Item[]> {
  return apiGet<Item[]>("/items", cookieHeader);
}

export function createItem(payload: ItemCreateInput): Promise<Item> {
  return apiPost<Item>("/items", payload);
}

export function getTaxes(cookieHeader?: string): Promise<Tax[]> {
  return apiGet<Tax[]>("/taxes", cookieHeader);
}

export function createTax(payload: TaxCreateInput): Promise<Tax> {
  return apiPost<Tax>("/taxes", payload);
}

export function getDashboardSummary(
  cookieHeader?: string,
): Promise<DashboardSummary> {
  return apiGet<DashboardSummary>("/dashboard/summary", cookieHeader);
}

export function getInvoices(cookieHeader?: string): Promise<Invoice[]> {
  return apiGet<Invoice[]>("/invoices", cookieHeader);
}

export function getInvoice(
  id: string,
  cookieHeader?: string,
): Promise<Invoice> {
  return apiGet<Invoice>(
    `/invoices/${encodeURIComponent(id)}`,
    cookieHeader,
  );
}

export function getInvoicePayments(
  id: string,
  cookieHeader?: string,
): Promise<Payment[]> {
  return apiGet<Payment[]>(
    `/invoices/${encodeURIComponent(id)}/payments`,
    cookieHeader,
  );
}

export function getContact(
  id: string,
  cookieHeader?: string,
): Promise<Contact> {
  return apiGet<Contact>(`/contacts/${encodeURIComponent(id)}`, cookieHeader);
}

export function createInvoice(
  payload: InvoiceCreateInput,
  idempotencyKey: string,
): Promise<Invoice> {
  return apiPost<Invoice>("/invoices", payload, {
    headers: { "Idempotency-Key": idempotencyKey },
  });
}

export function issueInvoice(invoiceId: string): Promise<Invoice> {
  return apiPost<Invoice>(`/invoices/${encodeURIComponent(invoiceId)}/issue`);
}

export function createPayment(
  invoiceId: string,
  payload: PaymentCreateInput,
  idempotencyKey: string,
): Promise<Payment> {
  return apiPost<Payment>(
    `/invoices/${encodeURIComponent(invoiceId)}/payments`,
    payload,
    {
      headers: { "Idempotency-Key": idempotencyKey },
    },
  );
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

export type QuoteStatus = "DRAFT" | "SENT" | "ACCEPTED" | "REJECTED" | "CONVERTED";

export interface QuoteLineInput {
  item_id: string;
  description?: string;
  quantity: string;
  unit_price: string;
  tax_rate: string;
}

export interface QuoteCreateInput {
  contact_id: string;
  issue_date: string;
  expiry_date: string;
  currency: "COP";
  lines: QuoteLineInput[];
}

export interface QuoteLine {
  id: string;
  item_id: string | null;
  description: string;
  quantity: string;
  unit_price: string;
  tax_rate: string;
  line_subtotal: string;
  line_tax: string;
  line_total: string;
}

export interface Quote {
  id: string;
  number: string | null;
  contact_id: string;
  contact_name: string;
  issue_date: string;
  expiry_date: string;
  currency: string;
  status: QuoteStatus;
  converted_invoice_id: string | null;
  converted_invoice_number: string | null;
  subtotal: string;
  tax_total: string;
  total: string;
  version: number;
  created_at: string;
  updated_at: string;
  lines: QuoteLine[];
}

export function getQuotes(cookieHeader?: string): Promise<Quote[]> {
  return apiGet<Quote[]>("/quotes", cookieHeader);
}

export function createQuote(
  payload: QuoteCreateInput,
  idempotencyKey: string,
): Promise<Quote> {
  return apiPost<Quote>("/quotes", payload, {
    headers: { "Idempotency-Key": idempotencyKey },
  });
}

export function getQuote(
  id: string,
  cookieHeader?: string,
): Promise<Quote> {
  return apiGet<Quote>(`/quotes/${encodeURIComponent(id)}`, cookieHeader);
}

export function deleteQuote(id: string): Promise<void> {
  return apiDelete<void>(`/quotes/${encodeURIComponent(id)}`);
}

export function convertQuoteToInvoice(id: string): Promise<Quote> {
  return apiPost<Quote>(
    `/quotes/${encodeURIComponent(id)}/convert-to-invoice`,
  );
}

export function updateQuoteStatus(
  id: string,
  status: QuoteStatus,
): Promise<Quote> {
  return apiPatch<Quote>(
    `/quotes/${encodeURIComponent(id)}/status`,
    { status },
  );
}

export function getWarehouses(cookieHeader?: string): Promise<Warehouse[]> {
  return apiGet<Warehouse[]>("/warehouses", cookieHeader);
}

/**
 * Descarga un reporte CSV protegido por cookie.
 *
 * Solo se usa desde el navegador (Client Components): reenvía la cookie de
 * sesión automáticamente con `credentials: "include"`, obtiene el blob y
 * fuerza la descarga mediante un enlace temporal.
 */
export async function downloadInvoicesCsv(): Promise<void> {
  return downloadFile(
    "/api/v1/reports/invoices.csv",
    "facturas.csv",
    "No se pudo descargar el listado de facturas",
  );
}

export async function downloadPaymentsCsv(): Promise<void> {
  return downloadFile(
    "/api/v1/reports/payments.csv",
    "pagos.csv",
    "No se pudo descargar el listado de pagos",
  );
}

async function errorDetail(response: Response, fallback: string): Promise<string> {
  try {
    const body = (await response.json()) as { detail?: unknown; message?: unknown };
    const detail = body.detail ?? body.message;
    if (typeof detail === "string") {
      return detail;
    }
    if (Array.isArray(detail)) {
      const messages = detail
        .map((item) => {
          if (typeof item === "string") return item;
          if (item && typeof item === "object" && "msg" in item) {
            return String((item as { msg: unknown }).msg);
          }
          return "";
        })
        .filter(Boolean);
      if (messages.length > 0) {
        return messages.join("; ");
      }
    }
  } catch {
    // La respuesta de error no era JSON.
  }
  return fallback;
}

function filenameFromDisposition(disposition: string | null): string | null {
  if (!disposition) {
    return null;
  }
  const encoded = disposition.match(/filename\*=UTF-8''([^;]+)/i);
  if (encoded?.[1]) {
    try {
      return decodeURIComponent(encoded[1]);
    } catch {
      return encoded[1];
    }
  }
  const quoted = disposition.match(/filename="([^"]+)"/i);
  if (quoted?.[1]) {
    return quoted[1];
  }
  const plain = disposition.match(/filename=([^;]+)/i);
  return plain?.[1]?.trim() ?? null;
}

/**
 * Descarga un archivo protegido por cookie con manejo uniforme de errores.
 *
 * No descarga nada si el backend responde 4xx/5xx o si devuelve JSON por
 * error. Si la respuesta es válida, usa el nombre del header
 * `Content-Disposition` y cae al nombre proporcionado como fallback.
 */
export async function downloadFile(
  path: string,
  fallbackFileName: string,
  errorLabel = "No se pudo descargar el archivo",
): Promise<void> {
  const response = await fetch(path, {
    credentials: "include",
    cache: "no-store",
  });

  const fallback = `${response.status} ${response.statusText}`.trim();
  if (!response.ok) {
    const detail = await errorDetail(response, fallback);
    throw new ApiError(`${errorLabel}: ${detail}`, response.status);
  }

  const contentType = response.headers.get("Content-Type") ?? "";
  if (contentType.includes("application/json")) {
    const detail = await errorDetail(response, fallback);
    throw new ApiError(`${errorLabel}: ${detail}`, response.status);
  }

  const fileName =
    filenameFromDisposition(response.headers.get("Content-Disposition")) ??
    fallbackFileName;
  const buffer = await response.arrayBuffer();
  const blob = new Blob([buffer], { type: contentType || "application/octet-stream" });
  const url = URL.createObjectURL(blob);

  const link = document.createElement("a");
  link.href = url;
  link.download = fileName;
  link.rel = "noopener";
  link.style.display = "none";
  document.body.appendChild(link);
  try {
    link.click();
  } catch {
    // Fallback para navegadores/webviews que bloquean clicks programáticos
    // sobre blob URLs: deja que el navegador gestione la descarga nativa.
    if (typeof window !== "undefined") {
      window.location.assign(path);
    }
    return;
  }
  // Mantener el ancla en el DOM mientras el navegador procesa la descarga.
  // Retirarla de inmediato puede cancelarla en Firefox/Safari.
  window.setTimeout(() => link.remove(), 5000);
  // Revocar el blob demasiado pronto también puede cancelar la descarga.
  window.setTimeout(() => URL.revokeObjectURL(url), 60_000);
}

export function createWarehouse(
  payload: WarehouseCreateInput,
): Promise<Warehouse> {
  return apiPost<Warehouse>("/warehouses", payload);
}

export function getExpenses(cookieHeader?: string): Promise<Expense[]> {
  return apiGet<Expense[]>("/expenses", cookieHeader);
}

export function createExpense(
  payload: ExpenseCreateInput,
): Promise<Expense> {
  return apiPost<Expense>("/expenses", payload);
}

export function getFixedAssets(cookieHeader?: string): Promise<FixedAsset[]> {
  return apiGet<FixedAsset[]>("/assets", cookieHeader);
}

export function createFixedAsset(
  payload: FixedAssetCreateInput,
): Promise<FixedAsset> {
  return apiPost<FixedAsset>("/assets", payload);
}

export function depreciateFixedAsset(
  assetId: string,
  payload: DepreciateAssetInput,
): Promise<FixedAsset> {
  return apiPost<FixedAsset>(
    `/assets/${encodeURIComponent(assetId)}/depreciate`,
    payload,
  );
}

export type BankAccountType = "CHECKING" | "SAVINGS";

export interface BankAccount {
  id: string;
  name: string;
  bank_name: string;
  account_number: string;
  account_type: BankAccountType;
  currency: string;
  accounting_account_code: string;
  accounting_account_name: string;
  is_active: boolean;
  balance: string;
  reconciled_balance: string;
  unreconciled_balance: string;
  unreconciled_transactions: number;
  version: number;
  created_at: string;
  updated_at: string;
}

export interface BankAccountCreateInput {
  name: string;
  bank_name: string;
  account_number: string;
  account_type: BankAccountType;
  currency: "COP";
  accounting_account_code: string;
}

export interface BankAccountUpdateInput {
  name?: string;
  is_active?: boolean;
  version: number;
}

export type BankTransactionType = "DEPOSIT" | "WITHDRAWAL" | "TRANSFER";

export interface BankTransaction {
  id: string;
  bank_account_id: string;
  bank_account_name: string;
  transaction_type: BankTransactionType;
  date: string;
  amount: string;
  description: string;
  reference: string | null;
  counterpart_account_id: string | null;
  counterpart_account_name: string | null;
  counterpart_account_code: string | null;
  is_reconciled: boolean;
  reconciled_at: string | null;
  version: number;
  created_at: string;
  updated_at: string;
}

export interface BankTransactionCreateInput {
  transaction_type: BankTransactionType;
  date: string;
  amount: string;
  description: string;
  reference?: string;
  counterpart_account_id?: string;
  counterpart_account_code?: string;
}

export type ReconciliationTransactionKind = "payment" | "expense";

export interface ReconciliationTransactionCandidate {
  id: string;
  kind: ReconciliationTransactionKind;
  date: string;
  amount: string;
  description: string;
  reference: string | null;
  party_name: string;
  invoice_number: string | null;
}

export interface ReconciliationBankMovement {
  id: string;
  date: string;
  amount: string;
  transaction_type: BankTransactionType;
  description: string;
  reference: string | null;
  version: number;
  candidates: ReconciliationTransactionCandidate[];
}

export interface ReconciliationCandidates {
  bank_account_id: string;
  bank_movements: ReconciliationBankMovement[];
}

export interface ReconcileBankMovementInput {
  bank_movement_id: string;
  transaction_id: string;
}

export interface ReconcileBankMovementResult {
  bank_account_id: string;
  bank_movement_id: string;
  bank_movement_date: string;
  bank_movement_amount: string;
  transaction: ReconciliationTransactionCandidate;
  is_reconciled: boolean;
  reconciled_at: string;
}

export interface TreasurySummary {
  total_balance: string;
  total_reconciled_balance: string;
  total_unreconciled_balance: string;
  total_accounts: number;
  active_accounts: number;
  unreconciled_transactions: number;
}

export interface AccountingAccount {
  code: string;
  name: string;
  account_type: string;
  nature: string;
  parent_code: string | null;
}

export function getTreasuryPucAccounts(
  cookieHeader?: string,
): Promise<AccountingAccount[]> {
  return apiGet<AccountingAccount[]>("/treasury/puc-accounts", cookieHeader);
}

export function getBankAccounts(
  cookieHeader?: string,
): Promise<BankAccount[]> {
  return apiGet<BankAccount[]>("/treasury/accounts", cookieHeader);
}

export function getBankAccount(
  id: string,
  cookieHeader?: string,
): Promise<BankAccount> {
  return apiGet<BankAccount>(
    `/treasury/accounts/${encodeURIComponent(id)}`,
    cookieHeader,
  );
}

export function createBankAccount(
  payload: BankAccountCreateInput,
): Promise<BankAccount> {
  return apiPost<BankAccount>("/treasury/accounts", payload);
}

export function updateBankAccount(
  id: string,
  payload: BankAccountUpdateInput,
): Promise<BankAccount> {
  return apiPatch<BankAccount>(
    `/treasury/accounts/${encodeURIComponent(id)}`,
    payload,
  );
}

export function getBankTransactions(
  accountId: string,
  cookieHeader?: string,
): Promise<BankTransaction[]> {
  return apiGet<BankTransaction[]>(
    `/treasury/accounts/${encodeURIComponent(accountId)}/transactions`,
    cookieHeader,
  );
}

export function createBankTransaction(
  accountId: string,
  payload: BankTransactionCreateInput,
): Promise<BankTransaction> {
  return apiPost<BankTransaction>(
    `/treasury/accounts/${encodeURIComponent(accountId)}/transactions`,
    payload,
  );
}

export function reconcileBankTransaction(
  transactionId: string,
  version: number,
): Promise<BankTransaction> {
  return apiPost<BankTransaction>(
    `/treasury/transactions/${encodeURIComponent(transactionId)}/reconcile`,
    { version },
  );
}

export function unreconcileBankTransaction(
  transactionId: string,
  version: number,
): Promise<BankTransaction> {
  return apiPost<BankTransaction>(
    `/treasury/transactions/${encodeURIComponent(transactionId)}/unreconcile`,
    { version },
  );
}

export function getReconciliationCandidates(
  accountId: string,
  cookieHeader?: string,
): Promise<ReconciliationCandidates> {
  return apiGet<ReconciliationCandidates>(
    `/banks/${encodeURIComponent(accountId)}/reconciliation-candidates`,
    cookieHeader,
  );
}

export function reconcileBankMovement(
  accountId: string,
  payload: ReconcileBankMovementInput,
): Promise<ReconcileBankMovementResult> {
  return apiPost<ReconcileBankMovementResult>(
    `/banks/${encodeURIComponent(accountId)}/reconcile`,
    payload,
  );
}

export function getTreasurySummary(
  cookieHeader?: string,
): Promise<TreasurySummary> {
  return apiGet<TreasurySummary>("/treasury/summary", cookieHeader);
}

export function getStockBalances(
  cookieHeader?: string,
): Promise<StockBalance[]> {
  return apiGet<StockBalance[]>("/inventory/balances", cookieHeader);
}

export function registerMovement(
  payload: StockMovementInput,
): Promise<StockMovement> {
  return apiPost<StockMovement>("/inventory/movements", payload);
}

export function getEmployees(cookieHeader?: string): Promise<Employee[]> {
  return apiGet<Employee[]>("/employees", cookieHeader);
}

export function createEmployee(payload: EmployeeCreateInput): Promise<Employee> {
  return apiPost<Employee>("/employees", payload);
}

export function getPayrollPeriods(
  cookieHeader?: string,
): Promise<PayrollPeriod[]> {
  return apiGet<PayrollPeriod[]>("/payroll/periods", cookieHeader);
}

export function createPayrollPeriod(
  payload: PayrollPeriodCreateInput,
): Promise<PayrollPeriod> {
  return apiPost<PayrollPeriod>("/payroll/periods", payload);
}

export function calculatePayroll(periodId: string): Promise<PayrollPeriod> {
  return apiPost<PayrollPeriod>(
    `/payroll/periods/${encodeURIComponent(periodId)}/calculate`,
  );
}

export function register(payload: RegisterInput): Promise<User> {
  return apiPost<User>("/auth/register", payload);
}

export function login(payload: LoginInput): Promise<User> {
  return apiPost<User>("/auth/login", payload);
}

export function logout(): Promise<void> {
  return apiPost<void>("/auth/logout");
}

export function getCurrentUser(cookieHeader?: string): Promise<User> {
  return apiGet<User>("/auth/me", cookieHeader);
}

export function switchCompany(companyId: string): Promise<User> {
  return apiPost<User>(
    `/auth/switch-company/${encodeURIComponent(companyId)}`,
  );
}

export function getCompanies(
  cookieHeader?: string,
): Promise<CompanyMembership[]> {
  return apiGet<CompanyMembership[]>("/companies", cookieHeader);
}

export function createCompany(
  payload: CompanyCreateInput,
): Promise<Company> {
  return apiPost<Company>("/companies", payload);
}

export function getCompanyUsers(
  companyId: string,
  cookieHeader?: string,
): Promise<CompanyUser[]> {
  return apiGet<CompanyUser[]>(
    `/companies/${encodeURIComponent(companyId)}/users`,
    cookieHeader,
  );
}

export function assignCompanyUser(
  companyId: string,
  payload: CompanyUserAssignInput,
): Promise<CompanyUser> {
  return apiPost<CompanyUser>(
    `/companies/${encodeURIComponent(companyId)}/users`,
    payload,
  );
}

export function getCrmStages(cookieHeader?: string): Promise<CrmStage[]> {
  return apiGet<CrmStage[]>("/crm/stages", cookieHeader);
}

export function getCrmOpportunities(
  cookieHeader?: string,
): Promise<CrmOpportunity[]> {
  return apiGet<CrmOpportunity[]>("/crm/opportunities", cookieHeader);
}

export function getCrmOpportunity(
  id: string,
  cookieHeader?: string,
): Promise<CrmOpportunityDetail> {
  return apiGet<CrmOpportunityDetail>(
    `/crm/opportunities/${encodeURIComponent(id)}`,
    cookieHeader,
  );
}

export function createCrmOpportunity(
  payload: CrmOpportunityCreateInput,
): Promise<CrmOpportunity> {
  return apiPost<CrmOpportunity>("/crm/opportunities", payload);
}

export function moveCrmOpportunity(
  id: string,
  stageId: string,
): Promise<CrmOpportunity> {
  return apiPatch<CrmOpportunity>(
    `/crm/opportunities/${encodeURIComponent(id)}/move`,
    { stage_id: stageId },
  );
}

export function deleteCrmOpportunity(id: string): Promise<void> {
  return apiDelete<void>(`/crm/opportunities/${encodeURIComponent(id)}`);
}

export function addCrmActivity(
  opportunityId: string,
  payload: CrmActivityCreateInput,
): Promise<CrmActivity> {
  return apiPost<CrmActivity>(
    `/crm/opportunities/${encodeURIComponent(opportunityId)}/activities`,
    payload,
  );
}

export function convertCrmOpportunityToQuote(
  opportunityId: string,
): Promise<CrmOpportunity> {
  return apiPost<CrmOpportunity>(
    `/crm/opportunities/${encodeURIComponent(opportunityId)}/convert-to-quote`,
  );
}

export function getPurchases(cookieHeader?: string): Promise<Purchase[]> {
  return apiGet<Purchase[]>("/purchases", cookieHeader);
}

export function getPurchase(
  id: string,
  cookieHeader?: string,
): Promise<Purchase> {
  return apiGet<Purchase>(`/purchases/${encodeURIComponent(id)}`, cookieHeader);
}

export function createPurchase(
  payload: PurchaseCreateInput,
  idempotencyKey: string,
): Promise<Purchase> {
  return apiPost<Purchase>("/purchases", payload, {
    headers: { "Idempotency-Key": idempotencyKey },
  });
}

export function issuePurchase(purchaseId: string): Promise<Purchase> {
  return apiPost<Purchase>(
    `/purchases/${encodeURIComponent(purchaseId)}/issue`,
  );
}

export interface PosItemSearchResult {
  id: string;
  name: string;
  unit_price: string;
  tax_rate: string;
  stock_current: string;
}

export interface PosCheckoutInput extends Omit<InvoiceCreateInput, "contact_id"> {
  contact_id: string | null;
}

export interface PosCheckoutResult {
  invoice: Invoice;
  payment: Payment | null;
}

export function searchPosItems(
  q: string,
  cookieHeader?: string,
): Promise<PosItemSearchResult[]> {
  return apiGet<PosItemSearchResult[]>(`/pos/search?q=${encodeURIComponent(q)}`, cookieHeader);
}

export function checkoutPos(
  payload: PosCheckoutInput,
  idempotencyKey: string,
): Promise<PosCheckoutResult> {
  return apiPost<PosCheckoutResult>("/pos/checkout", payload, {
    headers: { "Idempotency-Key": idempotencyKey },
  });
}

export type PurchasePaymentStatus = "draft" | "issued" | "void";

export interface PurchasePayment {
  id: string;
  purchase_invoice_id: string;
  amount: string;
  payment_date: string;
  method: string;
  reference: string | null;
  created_at: string;
}

export interface PurchasePaymentCreateInput {
  amount: string;
  payment_date: string;
  method: string;
  reference?: string;
}

export function getPurchasePayments(
  purchaseId: string,
  cookieHeader?: string,
): Promise<PurchasePayment[]> {
  return apiGet<PurchasePayment[]>(
    `/purchases/${encodeURIComponent(purchaseId)}/payments`,
    cookieHeader,
  );
}

export function createPurchasePayment(
  purchaseId: string,
  payload: PurchasePaymentCreateInput,
  idempotencyKey: string,
): Promise<PurchasePayment> {
  return apiPost<PurchasePayment>(
    `/purchases/${encodeURIComponent(purchaseId)}/payments`,
    payload,
    {
      headers: { "Idempotency-Key": idempotencyKey },
    },
  );
}

export type CreditNoteStatus = "draft" | "issued";

export interface CreditNoteLine {
  id: string;
  invoice_line_id: string | null;
  description: string;
  quantity: string;
  unit_price: string;
  tax_rate: string;
  line_subtotal: string;
  line_tax: string;
  line_total: string;
}

export interface CreditNote {
  id: string;
  number: string | null;
  invoice_id: string;
  issue_date: string;
  status: CreditNoteStatus;
  subtotal: string;
  tax_total: string;
  total: string;
  version: number;
  created_at: string;
  updated_at: string;
  lines: CreditNoteLine[];
}

export interface CreditNoteLineInput {
  invoice_line_id?: string;
  description: string;
  quantity: string;
  unit_price: string;
  tax_rate: string;
}

export interface CreditNoteCreateInput {
  issue_date: string;
  lines: CreditNoteLineInput[];
}

export function getCreditNotes(
  invoiceId: string,
  cookieHeader?: string,
): Promise<CreditNote[]> {
  return apiGet<CreditNote[]>(
    `/invoices/${encodeURIComponent(invoiceId)}/credit-notes`,
    cookieHeader,
  );
}

export function createCreditNote(
  invoiceId: string,
  payload: CreditNoteCreateInput,
  idempotencyKey: string,
): Promise<CreditNote> {
  return apiPost<CreditNote>(
    `/invoices/${encodeURIComponent(invoiceId)}/credit-notes`,
    payload,
    {
      headers: { "Idempotency-Key": idempotencyKey },
    },
  );
}

export function issueCreditNote(
  invoiceId: string,
  creditNoteId: string,
): Promise<CreditNote> {
  return apiPost<CreditNote>(
    `/invoices/${encodeURIComponent(invoiceId)}/credit-notes/${encodeURIComponent(
      creditNoteId,
    )}/issue`,
  );
}

export interface AccountReportRow {
  code: string;
  name: string;
  balance: string;
}

export interface IncomeStatementPreviousPeriod {
  start_date: string;
  end_date: string;
  total_income: string;
  total_expenses: string;
  net_income: string;
}

export interface IncomeStatementResponse {
  income_accounts: AccountReportRow[];
  expense_accounts: AccountReportRow[];
  total_income: string;
  total_expenses: string;
  net_income: string;
  previous_period?: IncomeStatementPreviousPeriod | null;
}

export interface BalanceSheetPreviousPeriod {
  as_of_date: string;
  total_assets: string;
  total_liabilities: string;
  total_equity: string;
  balanced: boolean;
}

export interface BalanceSheetResponse {
  asset_accounts: AccountReportRow[];
  liability_accounts: AccountReportRow[];
  equity_accounts: AccountReportRow[];
  total_assets: string;
  total_liabilities: string;
  total_equity: string;
  balanced: boolean;
  previous_period?: BalanceSheetPreviousPeriod | null;
}

export interface AgingBucketSummary {
  key: string;
  label: string;
  total: string;
  invoice_count: number;
}

export interface AgingClientRow {
  contact_id: string;
  contact_name: string;
  total_balance: string;
  max_days_overdue: number;
  oldest_due_date: string | null;
  invoice_count: number;
  buckets: Record<string, string>;
}

export interface AgingReport {
  as_of: string;
  total_receivable: string;
  buckets: AgingBucketSummary[];
  clients: AgingClientRow[];
}

export interface CashFlowIncomeSources {
  customer_payments: string;
  bank_deposits: string;
}

export interface CashFlowExpenseSources {
  supplier_payments: string;
  expenses: string;
  bank_withdrawals: string;
}

export interface CashFlowMonth {
  month: string;
  income: string;
  expenses: string;
  net: string;
  income_sources: CashFlowIncomeSources;
  expense_sources: CashFlowExpenseSources;
}

export interface CashFlowProjection {
  horizon_days: number;
  due_within_30_days: string;
  overdue_balance: string;
  expected_collections: string;
  invoice_count: number;
}

export interface CashFlowReport {
  as_of: string;
  months: CashFlowMonth[];
  projection: CashFlowProjection;
}

export interface LedgerMovement {
  id: string;
  entry_id: string;
  entry_date: string;
  description: string;
  source_type: string;
  debit: string;
  credit: string;
  balance: string;
}

export interface LedgerReport {
  account_code: string;
  account_name: string;
  nature: string;
  start_date: string | null;
  end_date: string | null;
  opening_balance: string;
  total_debits: string;
  total_credits: string;
  closing_balance: string;
  movements: LedgerMovement[];
}

export type TrialBalanceType = "DEUDOR" | "ACREEDOR" | "NEUTRO";

export interface TrialBalanceRow {
  code: string;
  name: string;
  debit: string;
  credit: string;
  balance: string;
  balance_type: TrialBalanceType;
}

export interface TrialBalanceReport {
  as_of_date: string | null;
  accounts: TrialBalanceRow[];
  total_debit: string;
  total_credit: string;
  difference: string;
  balanced: boolean;
}

export type FiscalPeriodStatus = "OPEN" | "CLOSED";

export interface FiscalPeriod {
  id: string;
  month: number;
  year: number;
  status: FiscalPeriodStatus;
  closed_at: string | null;
  created_at: string;
}

export function getLedgerAccounts(
  search?: string,
  cookieHeader?: string,
): Promise<AccountingAccount[]> {
  const params = new URLSearchParams();
  if (search) params.set("search", search);
  const query = params.toString();
  return apiGet<AccountingAccount[]>(
    `/reports/ledger/accounts${query ? "?" + query : ""}`,
    cookieHeader,
  );
}

export function getLedger(
  accountCode: string,
  startDate?: string,
  endDate?: string,
): Promise<LedgerReport> {
  const params = new URLSearchParams({ account_code: accountCode });
  if (startDate) params.set("start_date", startDate);
  if (endDate) params.set("end_date", endDate);
  return apiGet<LedgerReport>(`/reports/ledger?${params.toString()}`);
}

export function getTrialBalance(
  asOfDate?: string,
  cookieHeader?: string,
): Promise<TrialBalanceReport> {
  const params = new URLSearchParams();
  if (asOfDate) params.set("as_of_date", asOfDate);
  const query = params.toString();
  return apiGet<TrialBalanceReport>(
    `/reports/trial-balance${query ? "?" + query : ""}`,
    cookieHeader,
  );
}

export function closePeriod(
  month: number,
  year: number,
): Promise<FiscalPeriod> {
  return apiPost<FiscalPeriod>("/accounting/close-period", { month, year });
}

export interface InitialCapitalInput {
  amount: string;
  entry_date?: string;
  bank_account_id?: string;
  description?: string;
}

export interface AccountingEntryLineRead {
  id: string;
  account_code: string;
  account_name: string;
  debit: string;
  credit: string;
}

export interface InitialCapitalEntry {
  id: string;
  entry_date: string;
  description: string;
  source_type: string;
  status: string;
  lines: AccountingEntryLineRead[];
  total_debit: string;
  total_credit: string;
}

export function registerInitialCapital(
  payload: InitialCapitalInput,
): Promise<InitialCapitalEntry> {
  return apiPost<InitialCapitalEntry>("/accounting/initial-capital", payload);
}

export function getIncomeStatement(
  startDate?: string,
  endDate?: string,
  cookieHeader?: string,
): Promise<IncomeStatementResponse> {
  const params = new URLSearchParams();
  if (startDate) params.set("start_date", startDate);
  if (endDate) params.set("end_date", endDate);
  const query = params.toString();
  return apiGet<IncomeStatementResponse>(
    `/reports/income-statement${query ? "?" + query : ""}`,
    cookieHeader,
  );
}

export function getBalanceSheet(
  asOfDate?: string,
  cookieHeader?: string,
): Promise<BalanceSheetResponse> {
  const params = new URLSearchParams();
  if (asOfDate) params.set("as_of_date", asOfDate);
  const query = params.toString();
  return apiGet<BalanceSheetResponse>(
    `/reports/balance-sheet${query ? "?" + query : ""}`,
    cookieHeader,
  );
}

export function getAgingReport(cookieHeader?: string): Promise<AgingReport> {
  return apiGet<AgingReport>("/reports/aging", cookieHeader);
}

export function getCashFlowReport(
  cookieHeader?: string,
): Promise<CashFlowReport> {
  return apiGet<CashFlowReport>("/reports/cash-flow", cookieHeader);
}

export interface CompanySetting {
  id: string;
  name: string;
  tax_id: string | null;
  address: string | null;
  phone: string | null;
  email: string | null;
  logo_url: string | null;
  dv: string | null;
  tax_regime: string | null;
  person_type: string | null;
  fiscal_responsibility: string | null;
  dian_municipality_code: string | null;
  dian_department_code: string | null;
  country_code: string;
  dian_resolution_number: string | null;
  dian_resolution_prefix: string | null;
  dian_resolution_range_from: number | null;
  dian_resolution_range_to: number | null;
  dian_resolution_valid_from: string | null;
  dian_resolution_valid_to: string | null;
  dian_software_id: string | null;
  dian_software_pin: string | null;
  dian_environment: "HABILITACION" | "PRODUCCION";
  created_at: string;
  updated_at: string;
}

export interface CompanySettingCreateInput {
  name: string;
  tax_id?: string;
  address?: string;
  phone?: string;
  email?: string;
  logo_url?: string;
}

export interface CompanySettingUpdateInput {
  name?: string;
  tax_id?: string;
  address?: string;
  phone?: string;
  email?: string;
  logo_url?: string;
  dv?: string;
  tax_regime?: string;
  person_type?: string;
  fiscal_responsibility?: string;
  dian_municipality_code?: string;
  dian_department_code?: string;
  dian_resolution_number?: string;
  dian_resolution_prefix?: string;
  dian_resolution_range_from?: number;
  dian_resolution_range_to?: number;
  dian_resolution_valid_from?: string;
  dian_resolution_valid_to?: string;
  dian_software_id?: string;
  dian_software_pin?: string;
  dian_environment?: "HABILITACION" | "PRODUCCION";
}

export function getCompanySettings(
  cookieHeader?: string,
): Promise<CompanySetting> {
  return apiGet<CompanySetting>("/settings/company", cookieHeader);
}

export function updateCompanySettings(
  payload: CompanySettingUpdateInput,
): Promise<CompanySetting> {
  // El backend expone PUT /settings/company; usar POST devolvía 405.
  return apiPut<CompanySetting>("/settings/company", payload);
}

export interface UserItem {
  id: string;
  email: string;
  full_name: string;
  role: string;
  is_active: boolean;
  created_at: string;
}

export interface UserCreateInput {
  name: string;
  email: string;
  password: string;
  role: string;
}

export interface UserUpdateInput {
  name?: string;
  email?: string;
  password?: string;
  role?: string;
  is_active?: boolean;
}

export function getUsers(
  cookieHeader?: string,
): Promise<UserItem[]> {
  return apiGet<UserItem[]>("/users", cookieHeader);
}

export function createUser(
  payload: UserCreateInput,
  cookieHeader?: string,
): Promise<UserItem> {
  return apiPost<UserItem>("/users", payload, {
    headers: { "Idempotency-Key": crypto.randomUUID() },
  }, cookieHeader);
}

export function updateUser(
  userId: string,
  payload: UserUpdateInput,
  cookieHeader?: string,
): Promise<UserItem> {
  return apiPost<UserItem>(
    `/users/${encodeURIComponent(userId)}`,
    payload,
    { headers: { "Idempotency-Key": crypto.randomUUID() } },
    cookieHeader,
  );
}

// ---------------------------------------------------------------------------
// Notificaciones in-app
// ---------------------------------------------------------------------------

export type NotificationSeverity = "INFO" | "WARNING" | "CRITICAL";

export interface Notification {
  id: string;
  category: string;
  severity: NotificationSeverity;
  title: string;
  body: string | null;
  link: string | null;
  read_at: string | null;
  created_at: string;
}

export interface UnreadCount {
  count: number;
}

export interface MarkAllReadResult {
  marked: number;
}

export function getNotifications(
  query?: string,
  cookieHeader?: string,
): Promise<Notification[]> {
  return apiGet<Notification[]>(
    `/notifications${query ? "?" + query : ""}`,
    cookieHeader,
  );
}

export function getUnreadNotificationCount(): Promise<UnreadCount> {
  return apiGet<UnreadCount>("/notifications/unread-count");
}

export function markNotificationRead(id: string): Promise<void> {
  return apiPost<void>(
    `/notifications/${encodeURIComponent(id)}/mark-read`,
  );
}

export function markAllNotificationsRead(): Promise<MarkAllReadResult> {
  return apiPost<MarkAllReadResult>("/notifications/mark-all-read");
}

// ---------------------------------------------------------------------------
// Centros de costo y presupuestos
// ---------------------------------------------------------------------------

export interface CostCenter {
  id: string;
  code: string;
  name: string;
  description: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface CostCenterCreateInput {
  code: string;
  name: string;
  description?: string;
}

export interface CostCenterUpdateInput {
  code?: string;
  name?: string;
  description?: string;
  is_active?: boolean;
}

export function getCostCenters(
  includeInactive = false,
  cookieHeader?: string,
): Promise<CostCenter[]> {
  const params = new URLSearchParams();
  if (includeInactive) params.set("include_inactive", "true");
  const query = params.toString();
  return apiGet<CostCenter[]>(
    `/cost-centers${query ? "?" + query : ""}`,
    cookieHeader,
  );
}

export function createCostCenter(
  payload: CostCenterCreateInput,
): Promise<CostCenter> {
  return apiPost<CostCenter>("/cost-centers", payload);
}

export function updateCostCenter(
  id: string,
  payload: CostCenterUpdateInput,
): Promise<CostCenter> {
  return apiPatch<CostCenter>(
    `/cost-centers/${encodeURIComponent(id)}`,
    payload,
  );
}

export function deleteCostCenter(id: string): Promise<void> {
  return apiDelete<void>(`/cost-centers/${encodeURIComponent(id)}`);
}

export type BudgetStatus = "DRAFT" | "APPROVED" | "CLOSED";

export interface BudgetLine {
  id: string;
  account_code: string;
  account_name: string;
  amount: string;
  notes: string | null;
}

export interface Budget {
  id: string;
  cost_center: CostCenter;
  period_year: number;
  period_month: number;
  name: string | null;
  status: BudgetStatus;
  notes: string | null;
  lines: BudgetLine[];
  total: string;
  created_at: string;
  updated_at: string;
}

export interface BudgetCreateInput {
  cost_center_id: string;
  period_year: number;
  period_month: number;
  name?: string;
  notes?: string;
}

export interface BudgetLineCreateInput {
  account_code: string;
  amount: string;
  notes?: string;
}

export interface BudgetVsActualLine {
  account_code: string;
  account_name: string;
  budgeted: string;
  actual: string;
  variance: string;
  variance_pct: string | null;
  utilization_pct: string | null;
  alert_level: BudgetAlertLevel;
}

export interface BudgetVsActualTotals {
  budgeted: string;
  actual: string;
  variance: string;
  variance_pct: string | null;
  utilization_pct_total: string | null;
  alert_level_total: BudgetAlertLevel;
}

export interface BudgetVsActualResponse {
  budget_id: string;
  cost_center: CostCenter;
  period_year: number;
  period_month: number;
  status: BudgetStatus;
  lines: BudgetVsActualLine[];
  totals: BudgetVsActualTotals;
  has_alerts: boolean;
}

export type BudgetAlertLevel = "OK" | "WARNING" | "CRITICAL" | "OVER" | "N/A";

export interface BudgetAlertItem {
  budget_id: string;
  cost_center: { id: string; code: string; name: string };
  period_year: number;
  period_month: number;
  total_budgeted: string;
  total_actual: string;
  utilization_pct: string | null;
  alert_level: BudgetAlertLevel;
}

export interface BudgetVsActualReport {
  period_year: number;
  period_month: number;
  cost_center_id: string | null;
  blocks: BudgetVsActualResponse[];
}

export function getBudgets(
  query?: string,
  cookieHeader?: string,
): Promise<Budget[]> {
  return apiGet<Budget[]>(
    `/budgets${query ? "?" + query : ""}`,
    cookieHeader,
  );
}

export function getBudget(
  id: string,
  cookieHeader?: string,
): Promise<Budget> {
  return apiGet<Budget>(`/budgets/${encodeURIComponent(id)}`, cookieHeader);
}

export function createBudget(payload: BudgetCreateInput): Promise<Budget> {
  return apiPost<Budget>("/budgets", payload);
}

export function updateBudget(
  id: string,
  payload: { name?: string; notes?: string },
): Promise<Budget> {
  return apiPatch<Budget>(`/budgets/${encodeURIComponent(id)}`, payload);
}

export function deleteBudget(id: string): Promise<void> {
  return apiDelete<void>(`/budgets/${encodeURIComponent(id)}`);
}

export function addBudgetLine(
  budgetId: string,
  payload: BudgetLineCreateInput,
): Promise<BudgetLine> {
  return apiPost<BudgetLine>(
    `/budgets/${encodeURIComponent(budgetId)}/lines`,
    payload,
  );
}

export function updateBudgetLine(
  budgetId: string,
  lineId: string,
  payload: { amount?: string; notes?: string },
): Promise<BudgetLine> {
  return apiPatch<BudgetLine>(
    `/budgets/${encodeURIComponent(budgetId)}/lines/${encodeURIComponent(lineId)}`,
    payload,
  );
}

export function deleteBudgetLine(
  budgetId: string,
  lineId: string,
): Promise<void> {
  return apiDelete<void>(
    `/budgets/${encodeURIComponent(budgetId)}/lines/${encodeURIComponent(lineId)}`,
  );
}

export function approveBudget(budgetId: string): Promise<Budget> {
  return apiPost<Budget>(`/budgets/${encodeURIComponent(budgetId)}/approve`);
}

export function closeBudget(budgetId: string): Promise<Budget> {
  return apiPost<Budget>(`/budgets/${encodeURIComponent(budgetId)}/close`);
}

export function getBudgetActuals(
  budgetId: string,
): Promise<BudgetVsActualResponse> {
  return apiGet<BudgetVsActualResponse>(
    `/budgets/${encodeURIComponent(budgetId)}/actuals`,
  );
}

export function getBudgetAlerts(
  periodYear: number,
  periodMonth: number,
  level?: "WARNING" | "CRITICAL" | "OVER",
  cookieHeader?: string,
): Promise<BudgetAlertItem[]> {
  const params = new URLSearchParams({
    period_year: String(periodYear),
    period_month: String(periodMonth),
  });
  if (level) params.set("level", level);
  return apiGet<BudgetAlertItem[]>(
    `/budgets/alerts?${params.toString()}`,
    cookieHeader,
  );
}

export function getBudgetVsActualReport(
  periodYear: number,
  periodMonth: number,
  costCenterId?: string,
  cookieHeader?: string,
): Promise<BudgetVsActualReport> {
  const params = new URLSearchParams({
    period_year: String(periodYear),
    period_month: String(periodMonth),
  });
  if (costCenterId) params.set("cost_center_id", costCenterId);
  return apiGet<BudgetVsActualReport>(
    `/reports/budget-vs-actual?${params.toString()}`,
    cookieHeader,
  );
}

// -- Cartera y cobranza ----------------------------------------------------

export interface AgingBuckets {
  current: string;
  d0_30: string;
  d31_60: string;
  d61_90: string;
  d91_120: string;
  d120_plus: string;
  total: string;
}

export interface CustomerAging {
  contact_id: string;
  contact_name: string;
  current: string;
  d0_30: string;
  d31_60: string;
  d61_90: string;
  d91_120: string;
  d120_plus: string;
  total: string;
  total_overdue: string;
  invoice_count: number;
}

export interface AgingReport {
  as_of_date: string;
  buckets_totals: AgingBuckets;
  by_customer: CustomerAging[];
  total_overdue: string;
}

export interface ReceivablesSummary {
  as_of_date: string;
  buckets_totals: AgingBuckets;
  total_overdue: string;
  top_customers: CustomerAging[];
  customer_count: number;
}

export type StatementLineType = "INVOICE" | "PAYMENT" | "CREDIT_NOTE";

export interface StatementLine {
  date: string;
  type: StatementLineType;
  reference: string;
  description: string;
  debit: string;
  credit: string;
  running_balance: string;
}

export interface CustomerStatement {
  contact_id: string;
  contact_name: string;
  from_date: string;
  to_date: string;
  opening_balance: string;
  lines: StatementLine[];
  closing_balance: string;
}

export type ReminderChannel = "IN_APP" | "EMAIL" | "SMS" | "CALL";

export interface PaymentReminder {
  id: string;
  invoice_id: string;
  contact_id: string;
  level: number;
  channel: ReminderChannel;
  sent_at: string;
  notes: string | null;
  created_by: string;
  created_at: string;
}

export interface ReminderCreateInput {
  invoice_id: string;
  level: number;
  channel?: ReminderChannel;
  notes?: string;
}

export interface AutoRemindResult {
  created: number;
  skipped: number;
  errors: number;
}

export type AgreementStatus =
  | "ACTIVE"
  | "COMPLETED"
  | "BROKEN"
  | "CANCELLED";

export interface AgreementInstallment {
  id: string;
  due_date: string;
  amount: string;
  paid_amount: string;
  paid_at: string | null;
  balance: string;
}

export interface PaymentAgreement {
  id: string;
  contact_id: string;
  invoice_id: string | null;
  total_amount: string;
  installments: number;
  start_date: string;
  status: AgreementStatus;
  notes: string | null;
  created_by: string;
  created_at: string;
  updated_at: string;
  installment_items: AgreementInstallment[];
  paid_total: string;
  balance: string;
}

export interface AgreementCreateInput {
  contact_id: string;
  invoice_id?: string;
  total_amount: string;
  installments: number;
  start_date: string;
  frequency_days?: number;
  notes?: string;
}

export function getReceivablesAging(
  asOfDate?: string,
  cookieHeader?: string,
): Promise<AgingReport> {
  const query = asOfDate
    ? `?as_of_date=${encodeURIComponent(asOfDate)}`
    : "";
  return apiGet<AgingReport>(`/receivables/aging${query}`, cookieHeader);
}

export function getCustomerAging(
  contactId: string,
  asOfDate?: string,
  cookieHeader?: string,
): Promise<CustomerAging> {
  const query = asOfDate
    ? `?as_of_date=${encodeURIComponent(asOfDate)}`
    : "";
  return apiGet<CustomerAging>(
    `/receivables/aging/${encodeURIComponent(contactId)}${query}`,
    cookieHeader,
  );
}

export function getCustomerStatement(
  contactId: string,
  fromDate: string,
  toDate: string,
  cookieHeader?: string,
): Promise<CustomerStatement> {
  const params = new URLSearchParams({
    from_date: fromDate,
    to_date: toDate,
  });
  return apiGet<CustomerStatement>(
    `/receivables/customers/${encodeURIComponent(contactId)}/statement?${params.toString()}`,
    cookieHeader,
  );
}

export function getReceivablesSummary(
  asOfDate?: string,
  cookieHeader?: string,
): Promise<ReceivablesSummary> {
  const query = asOfDate
    ? `?as_of_date=${encodeURIComponent(asOfDate)}`
    : "";
  return apiGet<ReceivablesSummary>(
    `/receivables/summary${query}`,
    cookieHeader,
  );
}

export function createReminder(
  payload: ReminderCreateInput,
): Promise<PaymentReminder> {
  return apiPost<PaymentReminder>("/receivables/reminders", payload);
}

export function getReminders(
  query?: string,
  cookieHeader?: string,
): Promise<PaymentReminder[]> {
  return apiGet<PaymentReminder[]>(
    `/receivables/reminders${query ? "?" + query : ""}`,
    cookieHeader,
  );
}

export function runAutoReminders(
  asOfDate?: string,
): Promise<AutoRemindResult> {
  return apiPost<AutoRemindResult>("/receivables/reminders/auto", {
    as_of_date: asOfDate ?? null,
  });
}

export function getAgreements(
  query?: string,
  cookieHeader?: string,
): Promise<PaymentAgreement[]> {
  return apiGet<PaymentAgreement[]>(
    `/receivables/agreements${query ? "?" + query : ""}`,
    cookieHeader,
  );
}

export function getAgreement(
  id: string,
  cookieHeader?: string,
): Promise<PaymentAgreement> {
  return apiGet<PaymentAgreement>(
    `/receivables/agreements/${encodeURIComponent(id)}`,
    cookieHeader,
  );
}

export function createAgreement(
  payload: AgreementCreateInput,
): Promise<PaymentAgreement> {
  return apiPost<PaymentAgreement>("/receivables/agreements", payload);
}

export function payInstallment(
  agreementId: string,
  installmentId: string,
  amount: string,
): Promise<PaymentAgreement> {
  return apiPost<PaymentAgreement>(
    `/receivables/agreements/${encodeURIComponent(agreementId)}/installments/${encodeURIComponent(installmentId)}/pay`,
    { amount },
  );
}

export function cancelAgreement(id: string): Promise<PaymentAgreement> {
  return apiPost<PaymentAgreement>(
    `/receivables/agreements/${encodeURIComponent(id)}/cancel`,
  );
}

export function markAgreementBroken(id: string): Promise<PaymentAgreement> {
  return apiPost<PaymentAgreement>(
    `/receivables/agreements/${encodeURIComponent(id)}/mark-broken`,
  );
}

// -- Documentos DIAN (XML/PDF/CUFE, generación local Fase 38A) ---------------

export interface DianPreview {
  invoice_id: string;
  number: string | null;
  cufe: string;
  dian_status: DianDocumentStatus;
  environment: string;
  software_pin_active: boolean;
  xml: string;
}

export interface RegeneratedCufe {
  invoice_id: string;
  number: string | null;
  cufe: string;
  dian_status: DianDocumentStatus | null;
}

/**
 * Descarga el XML/PDF DIAN de una factura como blob y dispara la descarga
 * del navegador. Solo para facturas emitidas; el backend responde 422 si
 * faltan datos DIAN del emisor o del adquiriente.
 */
async function downloadInvoiceDocument(
  invoiceId: string,
  extension: "xml" | "pdf",
): Promise<void> {
  return downloadFile(
    `/api/v1/invoices/${encodeURIComponent(invoiceId)}/${extension}`,
    `FV-documento.${extension}`,
    "No se pudo descargar el documento DIAN",
  );
}

export function downloadInvoiceXml(invoiceId: string): Promise<void> {
  return downloadInvoiceDocument(invoiceId, "xml");
}

export function downloadInvoicePdf(invoiceId: string): Promise<void> {
  return downloadInvoiceDocument(invoiceId, "pdf");
}

export function regenerateInvoiceCufe(
  invoiceId: string,
): Promise<RegeneratedCufe> {
  return apiPost<RegeneratedCufe>(
    `/invoices/${encodeURIComponent(invoiceId)}/regenerate-cufe`,
  );
}


// -- Nómina electrónica DIAN (Fase 39A) ---------------------------------

async function downloadPayrollDocument(
  periodId: string,
  extension: "xml" | "pdf" | "pila",
): Promise<void> {
  return downloadFile(
    `/api/v1/payroll/periods/${encodeURIComponent(periodId)}/${extension}`,
    `NE-periodo.${extension}`,
    "No se pudo descargar el documento de nómina",
  );
}

export function downloadPayrollXml(periodId: string): Promise<void> {
  return downloadPayrollDocument(periodId, "xml");
}

export function downloadPayrollPdf(periodId: string): Promise<void> {
  return downloadPayrollDocument(periodId, "pdf");
}

export function downloadPayrollPila(periodId: string): Promise<void> {
  return downloadPayrollDocument(periodId, "pila");
}

// -- Reportes NIIF (Fase 39C) ------------------------------------------------

export interface NiifSection {
  label: string;
  accounts: { code: string; name: string; balance: string }[][];
  total: string;
  kind?: string;
}

export interface NiifIncomeStatement {
  from_date: string;
  to_date: string;
  sections: NiifSection[];
  revenue: string;
  cost_of_sales: string;
  gross_profit: string;
  total_expenses: string;
  pretax_income: string;
  income_tax: string;
  net_income: string;
}

export interface ReportAccountRow {
  code: string;
  name: string;
  balance: string;
}

export interface ReportComposition {
  [key: string]: string;
}

export interface NiifBalanceSheet {
  as_of_date: string;
  current_assets: string;
  non_current_assets: string;
  total_assets: string;
  current_liabilities: string;
  non_current_liabilities: string;
  total_liabilities: string;
  equity: string;
  period_result: string;
  total_equity: string;
  difference: string;
  asset_accounts: ReportAccountRow[];
  liability_accounts: ReportAccountRow[];
  equity_accounts: ReportAccountRow[];
  asset_composition: ReportComposition;
  liability_equity_composition: ReportComposition;
}

export interface DrillDownMovement {
  id: string;
  entry_id: string;
  entry_number: string;
  entry_date: string;
  description: string;
  debit: string;
  credit: string;
  balance: string;
}

export interface DrillDownReport {
  account_code: string;
  account_name: string;
  nature: string;
  from_date: string | null;
  to_date: string | null;
  opening_balance: string;
  total_debits: string;
  total_credits: string;
  closing_balance: string;
  movements: DrillDownMovement[];
}

export interface NiifCashFlow {
  from_date: string;
  to_date: string;
  net_income: string;
  depreciation: string;
  receivables_change: string;
  inventory_change: string;
  payables_change: string;
  operating_cash_flow: string;
  investing_cash_flow: string;
  financing_cash_flow: string;
  net_cash_change: string;
  opening_cash: string;
  closing_cash: string;
  bank_closing_cash: string;
}

export function getNiifIncomeStatement(
  fromDate: string,
  toDate: string,
  cookieHeader?: string,
): Promise<NiifIncomeStatement> {
  const params = new URLSearchParams({ from_date: fromDate, to_date: toDate });
  return apiGet<NiifIncomeStatement>(
    `/reports/niif/income-statement?${params}`,
    cookieHeader,
  );
}

export function getNiifBalanceSheet(
  asOfDate: string,
  cookieHeader?: string,
): Promise<NiifBalanceSheet> {
  const params = new URLSearchParams({ as_of_date: asOfDate });
  return apiGet<NiifBalanceSheet>(`/reports/niif/balance-sheet?${params}`, cookieHeader);
}

export function getNiifCashFlow(
  fromDate: string,
  toDate: string,
  cookieHeader?: string,
): Promise<NiifCashFlow> {
  const params = new URLSearchParams({ from_date: fromDate, to_date: toDate });
  return apiGet<NiifCashFlow>(`/reports/niif/cash-flow?${params}`, cookieHeader);
}

export function getDrillDownReport(
  accountCode: string,
  fromDate: string,
  toDate: string,
  cookieHeader?: string,
): Promise<DrillDownReport> {
  const params = new URLSearchParams({
    account_code: accountCode,
    from_date: fromDate,
    to_date: toDate,
  });
  return apiGet<DrillDownReport>(`/reports/drill-down?${params}`, cookieHeader);
}

export function getFinancialReportExportUrl(
  report: "income-statement" | "balance-sheet",
  params: { fromDate?: string; toDate?: string; asOfDate?: string },
): string {
  const search = new URLSearchParams({ report });
  if (params.fromDate) {
    search.set("from_date", params.fromDate);
  }
  if (params.toDate) {
    search.set("to_date", params.toDate);
  }
  if (params.asOfDate) {
    search.set("as_of_date", params.asOfDate);
  }
  return `/api/v1/reports/export/xlsx?${search.toString()}`;
}
