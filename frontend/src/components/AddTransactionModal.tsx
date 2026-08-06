import { useEffect, useState, type FormEvent } from "react";
import { X } from "lucide-react";
import { financeApi } from "../api/finsight";
import { todayISO } from "../lib/format";
import { emitDataChanged } from "../lib/events";
import type { Category } from "../types";

const INCOME_SOURCES = [
  "Salary",
  "Freelancing",
  "Business",
  "Rental Income",
  "Bonus",
  "Investment Returns",
  "Other Income",
];

type TxType = "expense" | "income";

type Props = {
  open: boolean;
  onClose: () => void;
  onSuccess?: (message: string) => void;
  defaultType?: TxType;
};

export default function AddTransactionModal({
  open,
  onClose,
  onSuccess,
  defaultType = "expense",
}: Props) {
  const [type, setType] = useState<TxType>(defaultType);
  const [categories, setCategories] = useState<Category[]>([]);
  const [categoryId, setCategoryId] = useState("");
  const [customCategory, setCustomCategory] = useState("");
  const [source, setSource] = useState(INCOME_SOURCES[0]);
  const [amount, setAmount] = useState("");
  const [date, setDate] = useState(todayISO());
  const [description, setDescription] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const reset = (nextType: TxType = defaultType) => {
    setType(nextType);
    setAmount("");
    setDate(todayISO());
    setDescription("");
    setCustomCategory("");
    setSource(INCOME_SOURCES[0]);
    setError("");
    if (categories[0]) setCategoryId(String(categories[0].id));
  };

  useEffect(() => {
    if (!open) return;
    setType(defaultType);
    setError("");
    financeApi.categories().then((cats) => {
      setCategories(cats);
      if (cats[0]) setCategoryId(String(cats[0].id));
    });
  }, [open, defaultType]);

  if (!open) return null;

  const addCustomCategory = async () => {
    if (!customCategory.trim()) return;
    const cat = await financeApi.createCategory({ name: customCategory.trim() });
    const cats = await financeApi.categories();
    setCategories(cats);
    setCategoryId(String(cat.id));
    setCustomCategory("");
  };

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError("");
    try {
      if (type === "expense") {
        await financeApi.createExpense({
          category_id: Number(categoryId),
          amount: Number(amount),
          description: description || null,
          merchant: null,
          expense_date: date,
        });
        emitDataChanged({ kind: "expense" });
        onSuccess?.("Expense added successfully.");
      } else {
        await financeApi.createIncome({
          source,
          amount: Number(amount),
          description: description || null,
          income_date: date,
        });
        emitDataChanged({ kind: "income" });
        onSuccess?.("Income added successfully.");
      }
      reset(type);
      onClose();
    } catch {
      setError("Could not save transaction. Please check the details and try again.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-[60] flex items-end justify-center bg-black/50 p-4 sm:items-center">
      <div
        className="absolute inset-0"
        onClick={onClose}
        aria-hidden
      />
      <div className="relative w-full max-w-md rounded-2xl border border-line bg-white p-5 shadow-2xl sm:p-6">
        <div className="mb-5 flex items-center justify-between">
          <div>
            <h2 className="text-xl font-semibold text-ink">Add Transaction</h2>
            <p className="mt-1 text-xs text-muted">Record income or an expense without leaving this page.</p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg p-2 text-muted hover:bg-sand hover:text-ink"
            aria-label="Close"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        <div className="mb-4 grid grid-cols-2 gap-2 rounded-xl bg-sand p-1">
          <button
            type="button"
            onClick={() => setType("expense")}
            className={`rounded-lg px-3 py-2.5 text-sm font-semibold transition ${
              type === "expense" ? "bg-white text-ink shadow-sm" : "text-muted hover:text-ink"
            }`}
          >
            Expense
          </button>
          <button
            type="button"
            onClick={() => setType("income")}
            className={`rounded-lg px-3 py-2.5 text-sm font-semibold transition ${
              type === "income" ? "bg-white text-ink shadow-sm" : "text-muted hover:text-ink"
            }`}
          >
            Income
          </button>
        </div>

        <form onSubmit={onSubmit} className="space-y-4">
          {type === "expense" ? (
            <>
              <label className="block space-y-2">
                <span className="text-sm font-medium text-ink">Category</span>
                <select
                  value={categoryId}
                  onChange={(e) => setCategoryId(e.target.value)}
                  required
                  className="w-full rounded-xl border border-line bg-white px-3 py-3 text-sm text-ink outline-none focus:border-moss/50"
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
                  className="flex-1 rounded-xl border border-line bg-white px-3 py-3 text-sm text-ink outline-none focus:border-moss/50"
                />
                <button
                  type="button"
                  onClick={addCustomCategory}
                  className="rounded-xl border border-line px-3 text-sm font-medium text-muted hover:text-ink"
                >
                  Add
                </button>
              </div>
            </>
          ) : (
            <label className="block space-y-2">
              <span className="text-sm font-medium text-ink">Category / Source</span>
              <select
                value={source}
                onChange={(e) => setSource(e.target.value)}
                className="w-full rounded-xl border border-line bg-white px-3 py-3 text-sm text-ink outline-none focus:border-moss/50"
              >
                {INCOME_SOURCES.map((s) => (
                  <option key={s}>{s}</option>
                ))}
              </select>
            </label>
          )}

          <label className="block space-y-2">
            <span className="text-sm font-medium text-ink">Amount (₹)</span>
            <input
              type="number"
              min="1"
              step="1"
              required
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
              className="w-full rounded-xl border border-line bg-white px-3 py-3 text-sm text-ink outline-none focus:border-moss/50"
              placeholder="0"
            />
          </label>

          <label className="block space-y-2">
            <span className="text-sm font-medium text-ink">Date</span>
            <input
              type="date"
              required
              value={date}
              onChange={(e) => setDate(e.target.value)}
              className="w-full rounded-xl border border-line bg-white px-3 py-3 text-sm text-ink outline-none focus:border-moss/50"
            />
          </label>

          <label className="block space-y-2">
            <span className="text-sm font-medium text-ink">Description</span>
            <input
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className="w-full rounded-xl border border-line bg-white px-3 py-3 text-sm text-ink outline-none focus:border-moss/50"
              placeholder="Optional note"
            />
          </label>

          {error ? <p className="text-sm text-danger">{error}</p> : null}

          <button
            type="submit"
            disabled={saving}
            className="w-full rounded-full bg-moss py-3 text-sm font-semibold text-white transition hover:bg-leaf disabled:opacity-60"
          >
            {saving ? "Saving…" : type === "expense" ? "Save expense" : "Save income"}
          </button>
        </form>
      </div>
    </div>
  );
}
