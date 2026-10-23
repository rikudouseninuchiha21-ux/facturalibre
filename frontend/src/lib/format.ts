export function formatCurrency(value: string, currency = "COP"): string {
  const amount = Number(value);

  if (!Number.isFinite(amount)) {
    return value;
  }

  try {
    return new Intl.NumberFormat("es-CO", {
      style: "currency",
      currency,
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(amount);
  } catch {
    return `${value} ${currency}`;
  }
}

const MONTH_NAMES = [
  "Enero",
  "Febrero",
  "Marzo",
  "Abril",
  "Mayo",
  "Junio",
  "Julio",
  "Agosto",
  "Septiembre",
  "Octubre",
  "Noviembre",
  "Diciembre",
] as const;

export function formatMonth(month: number): string {
  return MONTH_NAMES[month - 1] ?? `Mes ${month}`;
}

export function formatQuantity(value: string): string {
  const amount = Number(value);

  if (!Number.isFinite(amount)) {
    return value;
  }

  return new Intl.NumberFormat("es-CO", {
    minimumFractionDigits: 0,
    maximumFractionDigits: 4,
  }).format(amount);
}

export function formatTaxRate(value: string): string {
  const rate = Number(value);

  if (!Number.isFinite(rate)) {
    return `${value} %`;
  }

  return `${new Intl.NumberFormat("es-CO", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 4,
  }).format(rate)} %`;
}
