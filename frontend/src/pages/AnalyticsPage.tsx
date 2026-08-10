import { useEffect, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { analyticsApi } from "../api/finsight";
import { PageHeader, Panel, Stat } from "../components/ui";
import { onDataChanged } from "../lib/events";
import { currentYearMonth, money, pct } from "../lib/format";
import type { AnalyticsDashboard } from "../types";

const COLORS = ["#6366f1", "#22c55e", "#f59e0b", "#ef4444", "#06b6d4", "#a855f7", "#f97316"];

export default function AnalyticsPage() {
  const { year, month } = currentYearMonth();
  const [data, setData] = useState<AnalyticsDashboard | null>(null);

  useEffect(() => {
    analyticsApi.dashboard(year, month).then(setData);
  }, [year, month]);

  useEffect(
    () => onDataChanged(() => {
      analyticsApi.dashboard(year, month).then(setData);
    }),
    [year, month],
  );

  if (!data) return <p className="text-muted">Loading analytics…</p>;

  const expensePie = data.expense_by_category.map((c) => ({
    name: c.category,
    value: Number(c.amount),
  }));

  const incomeBars = data.income_by_source.map((c) => ({
    name: c.category,
    amount: Number(c.amount),
  }));

  return (
    <div>
      <PageHeader
        title="Financial Analytics"
        subtitle="Intelligence from your income, expenses, budgets, and goals"
      />

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
        <Stat label="Net Savings" value={money(data.summary.net_savings)} />
        <Stat label="Savings Rate" value={pct(data.summary.savings_rate)} />
        <Stat
          label="Health Score"
          value={
            data.health_has_data === false
              ? "No Data"
              : `${Math.round(Number(data.health_score ?? data.summary.financial_health_score))}/100`
          }
        />
      </div>

      <div className="mt-6 grid gap-4 xl:grid-cols-2">
        <Panel>
          <h2 className="text-2xl font-semibold tracking-tight text-ink">Expense Distribution</h2>
          <div className="mt-4 h-72">
            {expensePie.length ? (
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie data={expensePie} dataKey="value" nameKey="name" outerRadius={100} label>
                    {expensePie.map((_, i) => (
                      <Cell key={i} fill={COLORS[i % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip formatter={(v) => money(Number(v))} />
                  <Legend />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <p className="text-sm text-muted">Add expenses to see category distribution.</p>
            )}
          </div>
        </Panel>

        <Panel>
          <h2 className="text-2xl font-semibold tracking-tight text-ink">Income by Source</h2>
          <div className="mt-4 h-72">
            {incomeBars.length ? (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={incomeBars}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                  <XAxis dataKey="name" stroke="#94a3b8" fontSize={12} />
                  <YAxis stroke="#94a3b8" fontSize={12} />
                  <Tooltip formatter={(v) => money(Number(v))} />
                  <Bar dataKey="amount" fill="#6366f1" radius={[8, 8, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <p className="text-sm text-muted">Add income to see source analytics.</p>
            )}
          </div>
        </Panel>
      </div>

      <div className="mt-6 grid gap-4 xl:grid-cols-2">
        <Panel>
          <h2 className="text-2xl font-semibold tracking-tight text-ink">Budget Analytics</h2>
          <ul className="mt-4 space-y-3">
            {data.budget_analytics.length ? (
              data.budget_analytics.map((b) => (
                <li key={b.category} className="rounded-xl bg-sand px-3 py-3 text-sm">
                  <div className="flex justify-between font-medium">
                    <span>{b.category}</span>
                    <span className="capitalize">{b.status.replace("_", " ")}</span>
                  </div>
                  <p className="text-muted">
                    {money(b.spent)} / {money(b.budget)} · {pct(b.utilization)}
                  </p>
                </li>
              ))
            ) : (
              <p className="text-sm text-muted">Set budgets to monitor utilization.</p>
            )}
          </ul>
        </Panel>

        <Panel>
          <h2 className="text-2xl font-semibold tracking-tight text-ink">Health Score Breakdown</h2>
          <ul className="mt-4 space-y-3">
            {(
              [
                ["spending_score", data.spending_score],
                ["savings_score", data.savings_score],
                ["budget_score", data.budget_score],
                ["goals_score", data.goals_score],
              ] as const
            ).map(([key, value]) => (
              <li key={key}>
                <div className="mb-1 flex justify-between text-sm">
                  <span className="capitalize">{key.replaceAll("_", " ")}</span>
                  <span>{Number(value ?? 0).toFixed(1)}/25</span>
                </div>
                <div className="h-2 rounded-full bg-stone/50">
                  <div
                    className="h-2 rounded-full bg-moss"
                    style={{ width: `${(Number(value ?? 0) / 25) * 100}%` }}
                  />
                </div>
              </li>
            ))}
          </ul>
        </Panel>
      </div>
    </div>
  );
}
