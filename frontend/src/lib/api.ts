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

export interface User {
  id: string;
  email: string;
  full_name: string;
  is_active: boolean;
  created_at: string;
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
  lines: InvoiceLineInput[];
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

async function apiPost<T>(
  path: string,
  body?: unknown,
  options?: ApiPostOptions,
): Promise<T> {
  const response = await fetch(`${getBaseUrl()}${API_PREFIX}${path}`, {
    method: "POST",
    headers: {
      Accept: "application/json",
      ...(body === undefined ? {} : { "Content-Type": "application/json" }),
      ...options?.headers,
    },
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

export function getItems(cookieHeader?: string): Promise<Item[]> {
  return apiGet<Item[]>("/items", cookieHeader);
}

export function getTaxes(cookieHeader?: string): Promise<Tax[]> {
  return apiGet<Tax[]>("/taxes", cookieHeader);
}

export function getInvoices(cookieHeader?: string): Promise<Invoice[]> {
  return apiGet<Invoice[]>("/invoices", cookieHeader);
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

export function voidInvoice(
  invoiceId: string,
  payload: VoidInvoiceInput,
): Promise<Invoice> {
  return apiPost<Invoice>(
    `/invoices/${encodeURIComponent(invoiceId)}/void`,
    payload,
  );
}

export function getWarehouses(cookieHeader?: string): Promise<Warehouse[]> {
  return apiGet<Warehouse[]>("/warehouses", cookieHeader);
}

export function createWarehouse(
  payload: WarehouseCreateInput,
): Promise<Warehouse> {
  return apiPost<Warehouse>("/warehouses", payload);
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
