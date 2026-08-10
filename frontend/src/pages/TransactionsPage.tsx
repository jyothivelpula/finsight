import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { Search } from "lucide-react";
import { financeApi } from "../api/finsight";
import { onDataChanged } from "../lib/events";
import { currentYearMonth, money } from "../lib/format";
import type { Category, Expense, Income } from "../types";

type TxRow = {
  id: string;
  date: string;
  kind: "income" | "expense";
  label: string;
  details: string;
  amount: number;
};

const MONTH_LABELS = [
  "JAN", "FEB", "MAR", "APR", "MAY", "JUN",
  "JUL", "AUG", "SEP", "OCT", "NOV", "DEC",
];

export default function TransactionsPage() {
  const { year, month } = currentYearMonth();
  const [categories, setCategories] = useState<Category[]>([]);
  const [incomes, setIncomes] = useState<Income[]>([]);
  const [expenses, setExpenses] = useState<Expense[]>([]);
  const [search, setSearch] = useState("");
  const [kindFilter, setKindFilter] = useState<"all" | "income" | "expense">("all");

  const load = async () => {
    const [cats, inc, exp] = await Promise.all([
      financeApi.categories(),
      financeApi.incomes(),
      financeApi.expenses(),
    ]);
    setCategories(cats);
    setIncomes(inc);
    setExpenses(exp);
  };

  useEffect(() => {
    load();
  }, []);

  useEffect(() => onDataChanged(() => {
    load();
  }), []);

  const categoryName = (id: number) => categories.find((c) => c.id === id)?.name || "—";

  const rows = useMemo(() => {
    const incomeRows: TxRow[] = incomes.map((item) => ({
      id: `income-${item.id}`,
      date: item.income_date,
      kind: "income",
      label: item.source,
      details: item.description || "—",
      amount: Number(item.amount),
    }));
    const expenseRows: TxRow[] = expenses.map((item) => ({
      id: `expense-${item.id}`,
      date: item.expense_date,
      kind: "expense",
      label: categoryName(item.category_id),
      details: item.description || item.merchant || "—",
      amount: Number(item.amount),
    }));
    return [...incomeRows, ...expenseRows].sort((a, b) => b.date.localeCompare(a.date));
  }, [incomes, expenses, categories]);

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    return rows.filter((row) => {
      const matchesKind = kindFilter === "all" || row.kind === kindFilter;
      const haystack = `${row.kind} ${row.label} ${row.details} ${row.amount}`.toLowerCase();
      return matchesKind && (!q || haystack.includes(q));
    });
  }, [rows, search, kindFilter]);

  const monthRows = useMemo(
    () =>
      rows.filter((row) => {
        const d = new Date(row.date);
        return d.getFullYear() === year && d.getMonth() + 1 === month;
      }),
    [rows, year, month],
  );

  const monthIncome = useMemo(
    () => monthRows.filter((r) => r.kind === "income").reduce((s, r) => s + r.amount, 0),
    [monthRows],
  );
  const monthExpense = useMemo(
    () => monthRows.filter((r) => r.kind === "expense").reduce((s, r) => s + r.amount, 0),
    [monthRows],
  );

  return (
    <div className="mx-auto max-w-6xl">
      <div className="mb-8 flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h1 className="text-4xl font-semibold tracking-tight text-ink">Transactions</h1>
          <p className="mt-2 text-sm text-muted">
            All income and expenses in one place. Manage them in{" "}
            <Link to="/app/income" className="font-semibold text-moss hover:underline">Income</Link>
            {" "}or{" "}
            <Link to="/app/expenses" className="font-semibold text-moss hover:underline">Expenses</Link>.
          </p>
        </div>
      </div>

      <div className="grid gap-4 sm:grid-cols-3">
        <div className="rounded-2xl border border-line bg-card px-5 py-5">
          <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-muted">
            {MONTH_LABELS[month - 1]} {year} Income
          </p>
          <p className="mt-3 text-3xl font-semibold tracking-tight text-emerald-600">{money(monthIncome)}</p>
        </div>
        <div className="rounded-2xl border border-line bg-card px-5 py-5">
          <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-muted">
            {MONTH_LABELS[month - 1]} {year} Expenses
          </p>
          <p className="mt-3 text-3xl font-semibold tracking-tight text-danger">{money(monthExpense)}</p>
        </div>
        <div className="rounded-2xl border border-line bg-card px-5 py-5">
          <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-muted">Records</p>
          <p className="mt-3 text-3xl font-semibold tracking-tight text-ink">{rows.length}</p>
        </div>
      </div>

      <div className="mt-5 flex flex-col gap-3 sm:flex-row">
        <label className="relative flex-1">
          <Search className="pointer-events-none absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-muted" />
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search transactions..."
            className="w-full rounded-xl border border-line bg-card py-3 pl-10 pr-3 text-sm text-ink outline-none placeholder:text-muted/70 focus:border-moss/50 focus:ring-2 focus:ring-moss/20"
          />
        </label>
        <select
          value={kindFilter}
          onChange={(e) => setKindFilter(e.target.value as "all" | "income" | "expense")}
          className="rounded-xl border border-line bg-card px-4 py-3 text-sm text-ink outline-none focus:border-moss/50 focus:ring-2 focus:ring-moss/20 sm:min-w-[180px]"
        >
          <option value="all">All types</option>
          <option value="income">Income</option>
          <option value="expense">Expenses</option>
        </select>
      </div>

      <div className="mt-5 min-h-[320px] rounded-2xl border border-line bg-card">
        {filtered.length === 0 ? (
          <div className="flex min-h-[320px] flex-col items-center justify-center px-6 py-16 text-center">
            <p className="text-xl font-semibold text-ink">No transactions yet</p>
            <p className="mt-2 max-w-sm text-sm text-muted">
              Add income or expenses to see them appear here.
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-line text-[11px] uppercase tracking-[0.14em] text-muted">
                  <th className="px-5 py-4 font-semibold">Date</th>
                  <th className="px-5 py-4 font-semibold">Type</th>
                  <th className="px-5 py-4 font-semibold">Category / Source</th>
                  <th className="px-5 py-4 font-semibold">Details</th>
                  <th className="px-5 py-4 text-right font-semibold">Amount</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((row) => (
                  <tr key={row.id} className="border-b border-line/70 last:border-0">
                    <td className="px-5 py-4 text-muted">{row.date}</td>
                    <td className="px-5 py-4">
                      <span
                        className={
                          row.kind === "income"
                            ? "rounded-full bg-emerald-50 px-2.5 py-1 text-xs font-semibold text-emerald-700"
                            : "rounded-full bg-rose-50 px-2.5 py-1 text-xs font-semibold text-rose-700"
                        }
                      >
                        {row.kind === "income" ? "Income" : "Expense"}
                      </span>
                    </td>
                    <td className="px-5 py-4 font-medium text-ink">{row.label}</td>
                    <td className="px-5 py-4 text-muted">{row.details}</td>
                    <td
                      className={`px-5 py-4 text-right font-semibold ${
                        row.kind === "income" ? "text-emerald-600" : "text-danger"
                      }`}
                    >
                      {row.kind === "income" ? "+" : "−"}
                      {money(row.amount)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
