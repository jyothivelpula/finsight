import { useEffect, useMemo, useState, type FormEvent } from "react";
import { Plus, Search, Trash2, X } from "lucide-react";
import { financeApi } from "../api/finsight";
import { currentYearMonth, money, todayISO } from "../lib/format";
import type { Category, Expense } from "../types";

const MONTH_LABELS = [
  "JAN", "FEB", "MAR", "APR", "MAY", "JUN",
  "JUL", "AUG", "SEP", "OCT", "NOV", "DEC",
];

export default function ExpensesPage() {
  const { year, month } = currentYearMonth();
  const [categories, setCategories] = useState<Category[]>([]);
  const [items, setItems] = useState<Expense[]>([]);
  const [search, setSearch] = useState("");
  const [categoryFilter, setCategoryFilter] = useState("all");
  const [open, setOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [categoryId, setCategoryId] = useState("");
  const [amount, setAmount] = useState("");
  const [description, setDescription] = useState("");
  const [merchant, setMerchant] = useState("");
  const [expenseDate, setExpenseDate] = useState(todayISO());
  const [customCategory, setCustomCategory] = useState("");

  const load = async () => {
    const [cats, expenses] = await Promise.all([
      financeApi.categories(),
      financeApi.expenses(),
    ]);
    setCategories(cats);
    setItems(expenses);
    if (!categoryId && cats[0]) setCategoryId(String(cats[0].id));
  };

  useEffect(() => {
    load();
  }, []);

  const categoryName = (id: number) => categories.find((c) => c.id === id)?.name || "—";

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    return items.filter((item) => {
      const matchesCategory =
        categoryFilter === "all" || String(item.category_id) === categoryFilter;
      const haystack = `${categoryName(item.category_id)} ${item.description || ""} ${item.merchant || ""} ${item.amount}`.toLowerCase();
      return matchesCategory && (!q || haystack.includes(q));
    });
  }, [items, search, categoryFilter, categories]);

  const monthItems = useMemo(
    () =>
      items.filter((item) => {
        const d = new Date(item.expense_date);
        return d.getFullYear() === year && d.getMonth() + 1 === month;
      }),
    [items, year, month],
  );

  const monthTotal = useMemo(
    () => monthItems.reduce((sum, item) => sum + Number(item.amount), 0),
    [monthItems],
  );

  const allTimeTotal = useMemo(
    () => items.reduce((sum, item) => sum + Number(item.amount), 0),
    [items],
  );

  const resetForm = () => {
    setAmount("");
    setDescription("");
    setMerchant("");
    setExpenseDate(todayISO());
    setCustomCategory("");
  };

  const addCustomCategory = async () => {
    if (!customCategory.trim()) return;
    const cat = await financeApi.createCategory({ name: customCategory.trim() });
    setCustomCategory("");
    await load();
    setCategoryId(String(cat.id));
  };

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setSaving(true);
    try {
      await financeApi.createExpense({
        category_id: Number(categoryId),
        amount: Number(amount),
        description: description || null,
        merchant: merchant || null,
        expense_date: expenseDate,
      });
      resetForm();
      setOpen(false);
      await load();
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="mx-auto max-w-6xl">
      <div className="mb-8 flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h1 className="text-4xl font-semibold tracking-tight text-white">Expenses</h1>
          <p className="mt-2 text-sm text-muted">Every rupee that goes out, by category.</p>
        </div>
        <button
          type="button"
          onClick={() => setOpen(true)}
          className="inline-flex items-center justify-center gap-2 rounded-full bg-moss px-5 py-2.5 text-sm font-semibold text-black transition hover:bg-leaf"
        >
          <Plus className="h-4 w-4" strokeWidth={2.5} />
          Add expense
        </button>
      </div>

      <div className="grid gap-4 sm:grid-cols-3">
        <div className="rounded-2xl border border-line bg-card px-5 py-5">
          <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-muted">
            {MONTH_LABELS[month - 1]} {year} TOTAL
          </p>
          <p className="mt-3 text-3xl font-semibold tracking-tight text-danger">{money(monthTotal)}</p>
        </div>
        <div className="rounded-2xl border border-line bg-card px-5 py-5">
          <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-muted">
            All-time total
          </p>
          <p className="mt-3 text-3xl font-semibold tracking-tight text-white">{money(allTimeTotal)}</p>
        </div>
        <div className="rounded-2xl border border-line bg-card px-5 py-5">
          <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-muted">Records</p>
          <p className="mt-3 text-3xl font-semibold tracking-tight text-white">{items.length}</p>
        </div>
      </div>

      <div className="mt-5 flex flex-col gap-3 sm:flex-row">
        <label className="relative flex-1">
          <Search className="pointer-events-none absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-muted" />
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search expenses..."
            className="w-full rounded-xl border border-line bg-card py-3 pl-10 pr-3 text-sm text-white outline-none placeholder:text-muted/70 focus:border-moss/50 focus:ring-2 focus:ring-moss/20"
          />
        </label>
        <select
          value={categoryFilter}
          onChange={(e) => setCategoryFilter(e.target.value)}
          className="rounded-xl border border-line bg-card px-4 py-3 text-sm text-white outline-none focus:border-moss/50 focus:ring-2 focus:ring-moss/20 sm:min-w-[180px]"
        >
          <option value="all">All categories</option>
          {categories.map((c) => (
            <option key={c.id} value={c.id}>
              {c.name}
            </option>
          ))}
        </select>
      </div>

      <div className="mt-5 min-h-[320px] rounded-2xl border border-line bg-card">
        {filtered.length === 0 ? (
          <div className="flex min-h-[320px] flex-col items-center justify-center px-6 py-16 text-center">
            <p className="text-xl font-semibold text-white">No expense records</p>
            <p className="mt-2 max-w-sm text-sm text-muted">
              Add your first expense to start tracking where your money goes.
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-line text-[11px] uppercase tracking-[0.14em] text-muted">
                  <th className="px-5 py-4 font-semibold">Date</th>
                  <th className="px-5 py-4 font-semibold">Category</th>
                  <th className="px-5 py-4 font-semibold">Details</th>
                  <th className="px-5 py-4 text-right font-semibold">Amount</th>
                  <th className="px-5 py-4" />
                </tr>
              </thead>
              <tbody>
                {filtered.map((item) => (
                  <tr key={item.id} className="border-b border-line/70 last:border-0">
                    <td className="px-5 py-4 text-muted">{item.expense_date}</td>
                    <td className="px-5 py-4 font-medium text-white">{categoryName(item.category_id)}</td>
                    <td className="px-5 py-4 text-muted">{item.description || item.merchant || "—"}</td>
                    <td className="px-5 py-4 text-right font-semibold text-danger">{money(item.amount)}</td>
                    <td className="px-5 py-4 text-right">
                      <button
                        type="button"
                        aria-label="Delete expense"
                        className="rounded-lg p-2 text-muted transition hover:bg-danger/10 hover:text-danger"
                        onClick={async () => {
                          await financeApi.deleteExpense(item.id);
                          load();
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
          <div className="w-full max-w-md rounded-2xl border border-line bg-[#111816] p-5 shadow-2xl sm:p-6">
            <div className="mb-5 flex items-center justify-between">
              <h2 className="text-xl font-semibold text-white">Add expense</h2>
              <button
                type="button"
                onClick={() => setOpen(false)}
                className="rounded-lg p-2 text-muted hover:bg-white/5 hover:text-white"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
            <form onSubmit={onSubmit} className="space-y-4">
              <label className="block space-y-2">
                <span className="text-sm text-white/85">Category</span>
                <select
                  value={categoryId}
                  onChange={(e) => setCategoryId(e.target.value)}
                  required
                  className="w-full rounded-xl border border-line bg-[#0d1210] px-3 py-3 text-sm text-white outline-none focus:border-moss/50"
                >
                  {categories.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.name}
                    </option>
                  ))}
                </select>
              </label>
              <div className="flex gap-2">
                <input
                  value={customCategory}
                  onChange={(e) => setCustomCategory(e.target.value)}
                  placeholder="Custom category"
                  className="flex-1 rounded-xl border border-line bg-[#0d1210] px-3 py-3 text-sm text-white outline-none focus:border-moss/50"
                />
                <button
                  type="button"
                  onClick={addCustomCategory}
                  className="rounded-xl border border-line px-3 text-sm text-muted hover:text-white"
                >
                  Add
                </button>
              </div>
              <label className="block space-y-2">
                <span className="text-sm text-white/85">Amount (₹)</span>
                <input
                  type="number"
                  min="1"
                  required
                  value={amount}
                  onChange={(e) => setAmount(e.target.value)}
                  className="w-full rounded-xl border border-line bg-[#0d1210] px-3 py-3 text-sm text-white outline-none focus:border-moss/50"
                />
              </label>
              <label className="block space-y-2">
                <span className="text-sm text-white/85">Date</span>
                <input
                  type="date"
                  required
                  value={expenseDate}
                  onChange={(e) => setExpenseDate(e.target.value)}
                  className="w-full rounded-xl border border-line bg-[#0d1210] px-3 py-3 text-sm text-white outline-none focus:border-moss/50"
                />
              </label>
              <label className="block space-y-2">
                <span className="text-sm text-white/85">Merchant</span>
                <input
                  value={merchant}
                  onChange={(e) => setMerchant(e.target.value)}
                  className="w-full rounded-xl border border-line bg-[#0d1210] px-3 py-3 text-sm text-white outline-none focus:border-moss/50"
                />
              </label>
              <label className="block space-y-2">
                <span className="text-sm text-white/85">Description</span>
                <input
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  className="w-full rounded-xl border border-line bg-[#0d1210] px-3 py-3 text-sm text-white outline-none focus:border-moss/50"
                />
              </label>
              <button
                type="submit"
                disabled={saving}
                className="w-full rounded-full bg-moss py-3 text-sm font-semibold text-black transition hover:bg-leaf disabled:opacity-60"
              >
                {saving ? "Saving…" : "Save expense"}
              </button>
            </form>
          </div>
        </div>
      ) : null}
    </div>
  );
}
