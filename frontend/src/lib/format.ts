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

const relativeTimeFormatter = new Intl.RelativeTimeFormat("es-CO", {
  numeric: "auto",
});

/**
 * Fecha relativa en es-CO: "hace 5 minutos", "ayer", "hace 3 días".
 * Solo para presentación de timestamps; no se usa para cálculos de dinero.
 */
export function formatRelativeTime(iso: string): string {
  const timestamp = new Date(iso).getTime();
  if (!Number.isFinite(timestamp)) {
    return iso;
  }

  const seconds = Math.round((timestamp - Date.now()) / 1000);
  const absoluteSeconds = Math.abs(seconds);

  if (absoluteSeconds < 60) {
    return relativeTimeFormatter.format(seconds, "second");
  }
  if (absoluteSeconds < 3600) {
    return relativeTimeFormatter.format(Math.round(seconds / 60), "minute");
  }
  if (absoluteSeconds < 86400) {
    return relativeTimeFormatter.format(Math.round(seconds / 3600), "hour");
  }
  if (absoluteSeconds < 604800) {
    return relativeTimeFormatter.format(Math.round(seconds / 86400), "day");
  }
  if (absoluteSeconds < 2629800) {
    return relativeTimeFormatter.format(Math.round(seconds / 604800), "week");
  }
  if (absoluteSeconds < 31557600) {
    return relativeTimeFormatter.format(Math.round(seconds / 2629800), "month");
  }
  return relativeTimeFormatter.format(Math.round(seconds / 31557600), "year");
}
