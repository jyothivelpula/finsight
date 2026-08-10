import { useEffect, useMemo, useState, type FormEvent } from "react";
import { Plus, Search, Trash2, X } from "lucide-react";
import { financeApi } from "../api/finsight";
import { emitDataChanged, onDataChanged } from "../lib/events";
import { currentYearMonth, money, todayISO } from "../lib/format";
import type { Income } from "../types";

const SOURCES = [
  "Salary",
  "Freelancing",
  "Business",
  "Rental Income",
  "Bonus",
  "Investment Returns",
  "Other Income",
];

const MONTH_LABELS = [
  "JAN",
  "FEB",
  "MAR",
  "APR",
  "MAY",
  "JUN",
  "JUL",
  "AUG",
  "SEP",
  "OCT",
  "NOV",
  "DEC",
];

export default function IncomePage() {
  const { year, month } = currentYearMonth();
  const [items, setItems] = useState<Income[]>([]);
  const [search, setSearch] = useState("");
  const [sourceFilter, setSourceFilter] = useState("all");
  const [open, setOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [source, setSource] = useState(SOURCES[0]);
  const [amount, setAmount] = useState("");
  const [description, setDescription] = useState("");
  const [incomeDate, setIncomeDate] = useState(todayISO());

  const load = async () => {
    const data = await financeApi.incomes();
    setItems(data);
  };

  useEffect(() => {
    load();
  }, []);

  useEffect(() => onDataChanged(() => {
    load();
  }), []);

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    return items.filter((item) => {
      const matchesSource = sourceFilter === "all" || item.source === sourceFilter;
      const matchesSearch =
        !q ||
        item.source.toLowerCase().includes(q) ||
        (item.description || "").toLowerCase().includes(q) ||
        String(item.amount).includes(q);
      return matchesSource && matchesSearch;
    });
  }, [items, search, sourceFilter]);

  const monthTotal = useMemo(
    () =>
      items
        .filter((item) => {
          const d = new Date(item.income_date);
          return d.getFullYear() === year && d.getMonth() + 1 === month;
        })
        .reduce((sum, item) => sum + Number(item.amount), 0),
    [items, year, month],
  );

  const allTimeTotal = useMemo(
    () => items.reduce((sum, item) => sum + Number(item.amount), 0),
    [items],
  );

  const resetForm = () => {
    setSource(SOURCES[0]);
    setAmount("");
    setDescription("");
    setIncomeDate(todayISO());
  };

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setSaving(true);
    try {
      await financeApi.createIncome({
        source,
        amount: Number(amount),
        description: description || null,
        income_date: incomeDate,
      });
      resetForm();
      setOpen(false);
      await load();
      emitDataChanged({ kind: "income" });
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="mx-auto max-w-6xl">
      <div className="mb-8 flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h1 className="text-4xl font-semibold tracking-tight text-ink">Income</h1>
          <p className="mt-2 text-sm text-muted">Every rupee that comes in, by source.</p>
        </div>
        <button
          type="button"
          onClick={() => setOpen(true)}
          className="inline-flex items-center justify-center gap-2 rounded-full bg-moss px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-leaf"
        >
          <Plus className="h-4 w-4" strokeWidth={2.5} />
          Add income
        </button>
      </div>

      <div className="grid gap-4 sm:grid-cols-3">
        <div className="rounded-2xl border border-line bg-card px-5 py-5">
          <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-muted">
            {MONTH_LABELS[month - 1]} {year} TOTAL
          </p>
          <p className="mt-3 text-3xl font-semibold tracking-tight text-emerald-600">{money(monthTotal)}</p>
        </div>
        <div className="rounded-2xl border border-line bg-card px-5 py-5">
          <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-muted">
            All-time total
          </p>
          <p className="mt-3 text-3xl font-semibold tracking-tight text-ink">{money(allTimeTotal)}</p>
        </div>
        <div className="rounded-2xl border border-line bg-card px-5 py-5">
          <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-muted">Records</p>
          <p className="mt-3 text-3xl font-semibold tracking-tight text-ink">{items.length}</p>
        </div>
      </div>

      <div className="mt-5 flex flex-col gap-3 sm:flex-row">
        <label className="relative flex-1">
          <Search className="pointer-events-none absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-muted" />
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search incomes..."
            className="w-full rounded-xl border border-line bg-card py-3 pl-10 pr-3 text-sm text-ink outline-none placeholder:text-muted/70 focus:border-moss/50 focus:ring-2 focus:ring-moss/20"
          />
        </label>
        <select
          value={sourceFilter}
          onChange={(e) => setSourceFilter(e.target.value)}
          className="rounded-xl border border-line bg-card px-4 py-3 text-sm text-ink outline-none focus:border-moss/50 focus:ring-2 focus:ring-moss/20 sm:min-w-[180px]"
        >
          <option value="all">All sources</option>
          {SOURCES.map((s) => (
            <option key={s} value={s}>
              {s}
            </option>
          ))}
        </select>
      </div>

      <div className="mt-5 min-h-[320px] rounded-2xl border border-line bg-card">
        {filtered.length === 0 ? (
          <div className="flex min-h-[320px] flex-col items-center justify-center px-6 py-16 text-center">
            <p className="text-xl font-semibold text-ink">No income records</p>
            <p className="mt-2 max-w-sm text-sm text-muted">
              Add your first income to start building your financial picture.
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-line text-[11px] uppercase tracking-[0.14em] text-muted">
                  <th className="px-5 py-4 font-semibold">Date</th>
                  <th className="px-5 py-4 font-semibold">Source</th>
                  <th className="px-5 py-4 font-semibold">Description</th>
                  <th className="px-5 py-4 text-right font-semibold">Amount</th>
                  <th className="px-5 py-4" />
                </tr>
              </thead>
              <tbody>
                {filtered.map((item) => (
                  <tr key={item.id} className="border-b border-line/70 last:border-0">
                    <td className="px-5 py-4 text-muted">{item.income_date}</td>
                    <td className="px-5 py-4 font-medium text-ink">{item.source}</td>
                    <td className="px-5 py-4 text-muted">{item.description || "—"}</td>
                    <td className="px-5 py-4 text-right font-semibold text-emerald-600">
                      {money(item.amount)}
                    </td>
                    <td className="px-5 py-4 text-right">
                      <button
                        type="button"
                        aria-label="Delete income"
                        className="rounded-lg p-2 text-muted transition hover:bg-danger/10 hover:text-danger"
                        onClick={async () => {
                          await financeApi.deleteIncome(item.id);
                          await load();
                          emitDataChanged({ kind: "income" });
                        }}
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {open ? (
        <div className="fixed inset-0 z-50 flex items-end justify-center bg-black/70 p-4 sm:items-center">
          <div className="w-full max-w-md rounded-2xl border border-line bg-white p-5 shadow-2xl sm:p-6">
            <div className="mb-5 flex items-center justify-between">
              <h2 className="text-xl font-semibold text-ink">Add income</h2>
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
                <span className="text-sm text-ink">Source</span>
                <select
                  value={source}
                  onChange={(e) => setSource(e.target.value)}
                  className="w-full rounded-xl border border-line bg-white px-3 py-3 text-sm text-ink outline-none focus:border-moss/50"
                >
                  {SOURCES.map((s) => (
                    <option key={s}>{s}</option>
                  ))}
                </select>
              </label>
              <label className="block space-y-2">
                <span className="text-sm text-ink">Amount (₹)</span>
                <input
                  type="number"
                  min="1"
                  required
                  value={amount}
                  onChange={(e) => setAmount(e.target.value)}
                  className="w-full rounded-xl border border-line bg-white px-3 py-3 text-sm text-ink outline-none focus:border-moss/50"
                  placeholder="0"
                />
              </label>
              <label className="block space-y-2">
                <span className="text-sm text-ink">Date</span>
                <input
                  type="date"
                  required
                  value={incomeDate}
                  onChange={(e) => setIncomeDate(e.target.value)}
                  className="w-full rounded-xl border border-line bg-white px-3 py-3 text-sm text-ink outline-none focus:border-moss/50"
                />
              </label>
              <label className="block space-y-2">
                <span className="text-sm text-ink">Description</span>
                <input
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  className="w-full rounded-xl border border-line bg-white px-3 py-3 text-sm text-ink outline-none focus:border-moss/50"
                  placeholder="Optional"
                />
              </label>
              <button
                type="submit"
                disabled={saving}
                className="w-full rounded-full bg-moss py-3 text-sm font-semibold text-white transition hover:bg-leaf disabled:opacity-60"
              >
                {saving ? "Saving…" : "Save income"}
              </button>
            </form>
          </div>
        </div>
      ) : null}
    </div>
  );
}
