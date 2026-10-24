/**
 * Cliente HTTP tipado para la API v1 de Nexus ERP.
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
  role: string;
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
  type: string;
  status: string;
  version: number;
  created_at: string;
  updated_at: string;
}

export interface ContactCreateInput {
  name: string;
  email?: string;
  tax_id?: string;
  type?: string;
  status?: string;
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

export interface Payment {
  id: string;
  invoice_id: string;
  amount: string;
  payment_date: string;
  method: string;
  reference: string | null;
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
  return downloadCsv("/api/v1/reports/invoices.csv", "facturas.csv");
}

export async function downloadPaymentsCsv(): Promise<void> {
  return downloadCsv("/api/v1/reports/payments.csv", "pagos.csv");
}

async function downloadCsv(path: string, fileName: string): Promise<void> {
  const response = await fetch(path, {
    credentials: "include",
    cache: "no-store",
  });

  if (!response.ok) {
    const fallback = `${response.status} ${response.statusText}`.trim();
    throw new Error(`Error al descargar ${path}: ${fallback}`);
  }

  const blob = await response.blob();
  const url = URL.createObjectURL(blob);

  const link = document.createElement("a");
  link.href = url;
  link.download = fileName;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
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

export function searchPosItems(
  q: string,
  cookieHeader?: string,
): Promise<PosItemSearchResult[]> {
  return apiGet<PosItemSearchResult[]>(`/pos/search?q=${encodeURIComponent(q)}`, cookieHeader);
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

export interface IncomeStatementResponse {
  income_accounts: AccountReportRow[];
  expense_accounts: AccountReportRow[];
  total_income: string;
  total_expenses: string;
  net_income: string;
}

export interface BalanceSheetResponse {
  asset_accounts: AccountReportRow[];
  liability_accounts: AccountReportRow[];
  equity_accounts: AccountReportRow[];
  total_assets: string;
  total_liabilities: string;
  total_equity: string;
  balanced: boolean;
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

export interface CompanySetting {
  id: string;
  name: string;
  tax_id: string | null;
  address: string | null;
  phone: string | null;
  email: string | null;
  logo_url: string | null;
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
}

export function getCompanySettings(
  cookieHeader?: string,
): Promise<CompanySetting> {
  return apiGet<CompanySetting>("/settings/company", cookieHeader);
}

export function updateCompanySettings(
  payload: CompanySettingUpdateInput,
): Promise<CompanySetting> {
  return apiPost<CompanySetting>("/settings/company", payload, {
    headers: { "Idempotency-Key": crypto.randomUUID() },
  });
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
