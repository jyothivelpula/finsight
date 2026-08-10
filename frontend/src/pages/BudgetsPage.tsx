import { useEffect, useMemo, useState, type FormEvent } from "react";
import { Plus, Search, Trash2, X } from "lucide-react";
import { financeApi } from "../api/finsight";
import { StatusPill } from "../components/ui";
import { emitDataChanged, onDataChanged } from "../lib/events";
import { currentYearMonth, money, pct } from "../lib/format";
import type { Budget, Category } from "../types";

const MONTH_LABELS = [
  "JAN", "FEB", "MAR", "APR", "MAY", "JUN",
  "JUL", "AUG", "SEP", "OCT", "NOV", "DEC",
];

export default function BudgetsPage() {
  const { year, month } = currentYearMonth();
  const [categories, setCategories] = useState<Category[]>([]);
  const [budgets, setBudgets] = useState<Budget[]>([]);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [open, setOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [categoryId, setCategoryId] = useState("");
  const [amount, setAmount] = useState("");

  const load = async () => {
    const [cats, data] = await Promise.all([
      financeApi.categories(),
      financeApi.budgets(year, month),
    ]);
    setCategories(cats);
    setBudgets(data);
    if (!categoryId && cats[0]) setCategoryId(String(cats[0].id));
  };

  useEffect(() => {
    load();
  }, []);

  useEffect(() => onDataChanged(() => {
    load();
  }), [year, month]);

  const nameOf = (id: number) => categories.find((c) => c.id === id)?.name || "—";

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    return budgets.filter((b) => {
      const matchesStatus = statusFilter === "all" || b.status === statusFilter;
      const haystack = `${nameOf(b.category_id)} ${b.amount} ${b.status}`.toLowerCase();
      return matchesStatus && (!q || haystack.includes(q));
    });
  }, [budgets, search, statusFilter, categories]);

  const totalBudget = useMemo(
    () => budgets.reduce((sum, b) => sum + Number(b.amount), 0),
    [budgets],
  );
  const totalSpent = useMemo(
    () => budgets.reduce((sum, b) => sum + Number(b.spent), 0),
    [budgets],
  );
  const avgUsage = useMemo(() => {
    if (!budgets.length) return 0;
    return budgets.reduce((sum, b) => sum + b.utilization, 0) / budgets.length;
  }, [budgets]);

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setSaving(true);
    try {
      await financeApi.createBudget({
        category_id: Number(categoryId),
        amount: Number(amount),
        year,
        month,
      });
      setAmount("");
      setOpen(false);
      await load();
      emitDataChanged({ kind: "transaction" });
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="mx-auto max-w-6xl">
      <div className="mb-8 flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h1 className="text-4xl font-semibold tracking-tight text-ink">Budgets</h1>
          <p className="mt-2 text-sm text-muted">
            Set limits by category and stay on track this month.
          </p>
        </div>
        <button
          type="button"
          onClick={() => setOpen(true)}
          className="inline-flex items-center justify-center gap-2 rounded-full bg-moss px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-leaf"
        >
          <Plus className="h-4 w-4" strokeWidth={2.5} />
          Add budget
        </button>
      </div>

      <div className="grid gap-4 sm:grid-cols-3">
        <div className="rounded-2xl border border-line bg-card px-5 py-5">
          <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-muted">
            {MONTH_LABELS[month - 1]} {year} BUDGET
          </p>
          <p className="mt-3 text-3xl font-semibold tracking-tight text-moss">{money(totalBudget)}</p>
        </div>
        <div className="rounded-2xl border border-line bg-card px-5 py-5">
          <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-muted">
            Spent so far
          </p>
          <p className="mt-3 text-3xl font-semibold tracking-tight text-ink">{money(totalSpent)}</p>
        </div>
        <div className="rounded-2xl border border-line bg-card px-5 py-5">
          <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-muted">
            Avg. usage
          </p>
          <p className="mt-3 text-3xl font-semibold tracking-tight text-ink">{pct(avgUsage)}</p>
        </div>
      </div>

      <div className="mt-5 flex flex-col gap-3 sm:flex-row">
        <label className="relative flex-1">
          <Search className="pointer-events-none absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-muted" />
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search budgets..."
            className="w-full rounded-xl border border-line bg-card py-3 pl-10 pr-3 text-sm text-ink outline-none placeholder:text-muted/70 focus:border-moss/50 focus:ring-2 focus:ring-moss/20"
          />
        </label>
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="rounded-xl border border-line bg-card px-4 py-3 text-sm text-ink outline-none focus:border-moss/50 focus:ring-2 focus:ring-moss/20 sm:min-w-[180px]"
        >
          <option value="all">All statuses</option>
          <option value="on_track">On track</option>
          <option value="warning">Warning</option>
          <option value="exceeded">Exceeded</option>
        </select>
      </div>

      <div className="mt-5 min-h-[320px] rounded-2xl border border-line bg-card">
        {filtered.length === 0 ? (
          <div className="flex min-h-[320px] flex-col items-center justify-center px-6 py-16 text-center">
            <p className="text-xl font-semibold text-ink">No budget records</p>
            <p className="mt-2 max-w-sm text-sm text-muted">
              Add your first budget to start controlling category spending.
            </p>
          </div>
        ) : (
          <ul className="divide-y divide-line">
            {filtered.map((b) => (
              <li key={b.id} className="px-5 py-5">
                <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                  <div>
                    <div className="flex items-center gap-3">
                      <p className="font-semibold text-ink">{nameOf(b.category_id)}</p>
                      <StatusPill status={b.status} />
                    </div>
                    <p className="mt-1 text-sm text-muted">
                      Spent {money(b.spent)} of {money(b.amount)} · Remaining {money(b.remaining)}
                    </p>
                  </div>
                  <div className="flex items-center gap-3 sm:min-w-[220px]">
                    <div className="flex-1">
                      <div className="mb-1 flex justify-between text-xs text-muted">
                        <span>{pct(b.utilization)} used</span>
                      </div>
                      <div className="h-2 rounded-full bg-stone/40">
                        <div
                          className={`h-2 rounded-full ${
                            b.status === "exceeded"
                              ? "bg-danger"
                              : b.status === "warning"
                                ? "bg-warn"
                                : "bg-mint"
                          }`}
                          style={{ width: `${Math.min(100, b.utilization)}%` }}
                        />
                      </div>
                    </div>
                    <button
                      type="button"
                      aria-label="Delete budget"
                      className="rounded-lg p-2 text-muted transition hover:bg-danger/10 hover:text-danger"
                      onClick={async () => {
                        await financeApi.deleteBudget(b.id);
                        await load();
                        emitDataChanged({ kind: "transaction" });
                      }}
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>

      {open ? (
        <div className="fixed inset-0 z-50 flex items-end justify-center bg-black/70 p-4 sm:items-center">
          <div className="w-full max-w-md rounded-2xl border border-line bg-white p-5 shadow-2xl sm:p-6">
            <div className="mb-5 flex items-center justify-between">
              <h2 className="text-xl font-semibold text-ink">Add budget</h2>
              <button
                type="button"
                onClick={() => setOpen(false)}
                className="rounded-lg p-2 text-muted hover:bg-sand hover:text-ink"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
            <form onSubmit={onSubmit} className="space-y-4">
              <label className="block space-y-2">
                <span className="text-sm text-ink">Category</span>
                <select
                  value={categoryId}
                  onChange={(e) => setCategoryId(e.target.value)}
                  className="w-full rounded-xl border border-line bg-white px-3 py-3 text-sm text-ink outline-none focus:border-moss/50"
                >
                  {categories.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.name}
                    </option>
                  ))}
                </select>
              </label>
              <label className="block space-y-2">
                <span className="text-sm text-ink">Budget amount (₹)</span>
                <input
                  type="number"
                  min="1"
                  required
                  value={amount}
                  onChange={(e) => setAmount(e.target.value)}
                  placeholder="e.g. 8000"
                  className="w-full rounded-xl border border-line bg-white px-3 py-3 text-sm text-ink outline-none focus:border-moss/50"
                />
              </label>
              <button
                type="submit"
                disabled={saving}
                className="w-full rounded-full bg-moss py-3 text-sm font-semibold text-white transition hover:bg-leaf disabled:opacity-60"
              >
                {saving ? "Saving…" : "Save budget"}
              </button>
            </form>
          </div>
        </div>
      ) : null}
    </div>
  );
}
