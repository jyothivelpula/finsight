import { useEffect, useMemo, useState, type FormEvent } from "react";
import { Plus, Search, Trash2, X } from "lucide-react";
import { financeApi } from "../api/finsight";
import { StatusPill } from "../components/ui";
import { emitDataChanged, onDataChanged } from "../lib/events";
import { money } from "../lib/format";
import type { Goal } from "../types";

export default function GoalsPage() {
  const [goals, setGoals] = useState<Goal[]>([]);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [open, setOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [name, setName] = useState("");
  const [target, setTarget] = useState("");
  const [current, setCurrent] = useState("0");
  const [targetDate, setTargetDate] = useState("");
  const [addOpen, setAddOpen] = useState<Goal | null>(null);
  const [addAmount, setAddAmount] = useState("1000");

  const load = async () => {
    setGoals(await financeApi.goals());
  };

  useEffect(() => {
    load();
  }, []);

  useEffect(() => onDataChanged(() => {
    load();
  }), []);

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    return goals.filter((g) => {
      const matchesStatus = statusFilter === "all" || g.status === statusFilter;
      const haystack = `${g.name} ${g.notes || ""} ${g.status}`.toLowerCase();
      return matchesStatus && (!q || haystack.includes(q));
    });
  }, [goals, search, statusFilter]);

  const totalTarget = useMemo(
    () => goals.reduce((sum, g) => sum + Number(g.target_amount), 0),
    [goals],
  );
  const totalSaved = useMemo(
    () => goals.reduce((sum, g) => sum + Number(g.current_amount), 0),
    [goals],
  );
  const avgProgress = useMemo(() => {
    if (!goals.length) return 0;
    return goals.reduce((sum, g) => sum + g.completion_percentage, 0) / goals.length;
  }, [goals]);

  const resetForm = () => {
    setName("");
    setTarget("");
    setCurrent("0");
    setTargetDate("");
  };

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setSaving(true);
    try {
      await financeApi.createGoal({
        name,
        target_amount: Number(target),
        current_amount: Number(current || 0),
        target_date: targetDate || null,
      });
      resetForm();
      setOpen(false);
      await load();
      emitDataChanged({ kind: "transaction" });
    } finally {
      setSaving(false);
    }
  };

  const onAddSavings = async (e: FormEvent) => {
    e.preventDefault();
    if (!addOpen) return;
    const value = Number(addAmount);
    if (!value) return;
    await financeApi.updateGoal(addOpen.id, {
      current_amount: Number(addOpen.current_amount) + value,
    });
    setAddOpen(null);
    setAddAmount("1000");
    await load();
    emitDataChanged({ kind: "transaction" });
  };

  return (
    <div className="mx-auto max-w-6xl">
      <div className="mb-8 flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h1 className="text-4xl font-semibold tracking-tight text-ink">Goals</h1>
          <p className="mt-2 text-sm text-muted">
            Save with purpose — emergency fund, vacation, and more.
          </p>
        </div>
        <button
          type="button"
          onClick={() => setOpen(true)}
          className="inline-flex items-center justify-center gap-2 rounded-full bg-moss px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-leaf"
        >
          <Plus className="h-4 w-4" strokeWidth={2.5} />
          Add goal
        </button>
      </div>

      <div className="grid gap-4 sm:grid-cols-3">
        <div className="rounded-2xl border border-line bg-card px-5 py-5">
          <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-muted">
            Total saved
          </p>
          <p className="mt-3 text-3xl font-semibold tracking-tight text-moss">{money(totalSaved)}</p>
        </div>
        <div className="rounded-2xl border border-line bg-card px-5 py-5">
          <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-muted">
            Target total
          </p>
          <p className="mt-3 text-3xl font-semibold tracking-tight text-ink">{money(totalTarget)}</p>
        </div>
        <div className="rounded-2xl border border-line bg-card px-5 py-5">
          <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-muted">
            Avg. progress
          </p>
          <p className="mt-3 text-3xl font-semibold tracking-tight text-ink">
            {avgProgress.toFixed(0)}%
          </p>
        </div>
      </div>

      <div className="mt-5 flex flex-col gap-3 sm:flex-row">
        <label className="relative flex-1">
          <Search className="pointer-events-none absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-muted" />
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search goals..."
            className="w-full rounded-xl border border-line bg-card py-3 pl-10 pr-3 text-sm text-ink outline-none placeholder:text-muted/70 focus:border-moss/50 focus:ring-2 focus:ring-moss/20"
          />
        </label>
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="rounded-xl border border-line bg-card px-4 py-3 text-sm text-ink outline-none focus:border-moss/50 focus:ring-2 focus:ring-moss/20 sm:min-w-[180px]"
        >
          <option value="all">All statuses</option>
          <option value="active">Active</option>
          <option value="completed">Completed</option>
          <option value="paused">Paused</option>
        </select>
      </div>

      <div className="mt-5 min-h-[320px] rounded-2xl border border-line bg-card">
        {filtered.length === 0 ? (
          <div className="flex min-h-[320px] flex-col items-center justify-center px-6 py-16 text-center">
            <p className="text-xl font-semibold text-ink">No goal records</p>
            <p className="mt-2 max-w-sm text-sm text-muted">
              Add your first savings goal to start building toward what matters.
            </p>
          </div>
        ) : (
          <ul className="divide-y divide-line">
            {filtered.map((g) => (
              <li key={g.id} className="px-5 py-5">
                <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-3">
                      <p className="font-semibold text-ink">{g.name}</p>
                      <StatusPill status={g.status} />
                    </div>
                    <p className="mt-1 text-sm text-muted">
                      {money(g.current_amount)} of {money(g.target_amount)} ·{" "}
                      {money(g.remaining_amount)} remaining
                      {g.target_date ? ` · by ${g.target_date}` : ""}
                    </p>
                    <div className="mt-3 h-2 max-w-md rounded-full bg-stone/40">
                      <div
                        className="h-2 rounded-full bg-mint"
                        style={{ width: `${Math.min(100, g.completion_percentage)}%` }}
                      />
                    </div>
                    <p className="mt-1 text-xs text-muted">{g.completion_percentage}% complete</p>
                  </div>
                  <div className="flex items-center gap-2">
                    <button
                      type="button"
                      onClick={() => {
                        setAddOpen(g);
                        setAddAmount("1000");
                      }}
                      className="rounded-full border border-line px-4 py-2 text-sm font-medium text-ink hover:bg-sand"
                    >
                      Add savings
                    </button>
                    <button
                      type="button"
                      aria-label="Delete goal"
                      className="rounded-lg p-2 text-muted transition hover:bg-danger/10 hover:text-danger"
                      onClick={async () => {
                        await financeApi.deleteGoal(g.id);
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
              <h2 className="text-xl font-semibold text-ink">Add goal</h2>
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
                <span className="text-sm text-ink">Goal name</span>
                <input
                  required
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="Emergency Fund"
                  className="w-full rounded-xl border border-line bg-white px-3 py-3 text-sm text-ink outline-none focus:border-moss/50"
                />
              </label>
              <label className="block space-y-2">
                <span className="text-sm text-ink">Target amount (₹)</span>
                <input
                  type="number"
                  min="1"
                  required
                  value={target}
                  onChange={(e) => setTarget(e.target.value)}
                  className="w-full rounded-xl border border-line bg-white px-3 py-3 text-sm text-ink outline-none focus:border-moss/50"
                />
              </label>
              <label className="block space-y-2">
                <span className="text-sm text-ink">Current amount (₹)</span>
                <input
                  type="number"
                  min="0"
                  value={current}
                  onChange={(e) => setCurrent(e.target.value)}
                  className="w-full rounded-xl border border-line bg-white px-3 py-3 text-sm text-ink outline-none focus:border-moss/50"
                />
              </label>
              <label className="block space-y-2">
                <span className="text-sm text-ink">Target date</span>
                <input
                  type="date"
                  value={targetDate}
                  onChange={(e) => setTargetDate(e.target.value)}
                  className="w-full rounded-xl border border-line bg-white px-3 py-3 text-sm text-ink outline-none focus:border-moss/50"
                />
              </label>
              <button
                type="submit"
                disabled={saving}
                className="w-full rounded-full bg-moss py-3 text-sm font-semibold text-white transition hover:bg-leaf disabled:opacity-60"
              >
                {saving ? "Saving…" : "Save goal"}
              </button>
            </form>
          </div>
        </div>
      ) : null}

      {addOpen ? (
        <div className="fixed inset-0 z-50 flex items-end justify-center bg-black/70 p-4 sm:items-center">
          <div className="w-full max-w-sm rounded-2xl border border-line bg-white p-5 shadow-2xl">
            <div className="mb-4 flex items-center justify-between">
              <h2 className="text-lg font-semibold text-ink">Add to {addOpen.name}</h2>
              <button
                type="button"
                onClick={() => setAddOpen(null)}
                className="rounded-lg p-2 text-muted hover:bg-sand hover:text-ink"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
            <form onSubmit={onAddSavings} className="space-y-4">
              <label className="block space-y-2">
                <span className="text-sm text-ink">Amount (₹)</span>
                <input
                  type="number"
                  min="1"
                  required
                  value={addAmount}
                  onChange={(e) => setAddAmount(e.target.value)}
                  className="w-full rounded-xl border border-line bg-white px-3 py-3 text-sm text-ink outline-none focus:border-moss/50"
                />
              </label>
              <button
                type="submit"
                className="w-full rounded-full bg-moss py-3 text-sm font-semibold text-white transition hover:bg-leaf"
              >
                Add savings
              </button>
            </form>
          </div>
        </div>
      ) : null}
    </div>
  );
}
