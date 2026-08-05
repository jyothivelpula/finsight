export function money(value: string | number | undefined | null): string {
  const n = Number(value ?? 0);
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  }).format(n);
}

export function pct(value: number | undefined | null): string {
  return `${Number(value ?? 0).toFixed(1)}%`;
}

export function todayISO(): string {
  return new Date().toISOString().slice(0, 10);
}

export function currentYearMonth() {
  const d = new Date();
  return { year: d.getFullYear(), month: d.getMonth() + 1 };
}
