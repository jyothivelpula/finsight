export function money(value: string | number | undefined | null): string {
  const n = Number(value ?? 0);
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  }).format(n);
}

/** Compact INR for dashboard KPIs: ₹1.17L, ₹23.9K */
export function moneyCompact(value: string | number | undefined | null): string {
  const n = Number(value ?? 0);
  const abs = Math.abs(n);
  const sign = n < 0 ? "-" : "";
  if (abs >= 100000) {
    const lakhs = abs / 100000;
    return `${sign}₹${lakhs.toFixed(lakhs >= 10 ? 1 : 2).replace(/\.00$/, "")}L`;
  }
  if (abs >= 1000) {
    const thousands = abs / 1000;
    return `${sign}₹${thousands.toFixed(thousands >= 100 ? 0 : 1).replace(/\.0$/, "")}K`;
  }
  return `${sign}${money(abs)}`;
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
