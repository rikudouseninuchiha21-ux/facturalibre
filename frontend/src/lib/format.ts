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
