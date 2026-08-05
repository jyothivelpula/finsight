import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { analyticsApi, financeApi } from "../api/finsight";
import { EmptyState, PageHeader, Panel, Stat } from "../components/ui";
import { currentYearMonth, money, pct } from "../lib/format";
import type { AnalyticsDashboard, Expense, Goal } from "../types";
import { useAppSelector } from "../store";

export default function Dashboard() {
  const user = useAppSelector((s) => s.auth.user);
  const { year, month } = currentYearMonth();
  const [data, setData] = useState<AnalyticsDashboard | null>(null);
  const [expenses, setExpenses] = useState<Expense[]>([]);
  const [goals, setGoals] = useState<Goal[]>([]);

  useEffect(() => {
    Promise.all([
      analyticsApi.dashboard(year, month),
      financeApi.expenses({ year, month }),
      financeApi.goals(),
    ]).then(([dash, exp, g]) => {
      setData(dash);
      setExpenses(exp.slice(0, 5));
      setGoals(g.filter((x) => x.status === "active").slice(0, 3));
    });
  }, [year, month]);

  if (!data) {
    return <p className="text-muted">Loading dashboard…</p>;
  }

  const chartData = data.monthly_trends.map((p) => ({
    period: p.period.slice(5),
    income: Number(p.income),
    expenses: Number(p.expenses),
  }));

  return (
    <div>
      <PageHeader
        title={`Hello, ${user?.full_name?.split(" ")[0] || "there"}`}
        subtitle="Your monthly financial overview"
        action={
          <Link to="/app/ai" className="rounded-xl bg-moss px-4 py-2.5 text-sm font-semibold text-black">
            Ask AI Assistant
          </Link>
        }
      />

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
        <Stat label="Monthly Income" value={money(data.summary.total_income)} />
        <Stat label="Monthly Expenses" value={money(data.summary.total_expenses)} />
        <Stat label="Total Savings" value={money(data.summary.net_savings)} />
        <Stat label="Savings Rate" value={pct(data.summary.savings_rate)} />
        <Stat label="Budget Usage" value={pct(data.summary.budget_usage)} />
        <Stat
          label="Financial Health Score"
          value={`${data.summary.financial_health_score}/100`}
          hint="Based on savings, budgets, goals & stability"
        />
      </div>

      <div className="mt-6 grid gap-4 xl:grid-cols-[1.4fr_1fr]">
        <Panel>
          <h2 className="text-2xl font-semibold tracking-tight text-white">Income vs Expenses</h2>
          <div className="mt-4 h-64">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#243029" />
                <XAxis dataKey="period" stroke="#9ca3af" />
                <YAxis stroke="#9ca3af" />
                <Tooltip formatter={(v) => money(Number(v))} contentStyle={{ background: "#161d19", border: "1px solid #243029" }} />
                <Area type="monotone" dataKey="income" stroke="#22c55e" fill="#22c55e" fillOpacity={0.25} />
                <Area type="monotone" dataKey="expenses" stroke="#f87171" fill="#f87171" fillOpacity={0.18} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </Panel>

        <Panel>
          <h2 className="text-2xl font-semibold tracking-tight text-white">AI Insights</h2>
          <ul className="mt-4 space-y-3">
            {data.insights.length ? (
              data.insights.slice(0, 6).map((insight) => (
                <li key={insight} className="rounded-xl bg-sand px-3 py-2 text-sm text-ink/90">
                  {insight}
                </li>
              ))
            ) : (
              <EmptyState
                title="No insights yet"
                body="Add income and expenses to generate smart insights."
              />
            )}
          </ul>
        </Panel>
      </div>

      <div className="mt-6 grid gap-4 lg:grid-cols-2">
        <Panel>
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-2xl font-semibold tracking-tight text-white">Recent Transactions</h2>
            <Link to="/app/expenses" className="text-sm font-semibold text-leaf">
              View all
            </Link>
          </div>
          {expenses.length ? (
            <ul className="divide-y divide-stone/60">
              {expenses.map((e) => (
                <li key={e.id} className="flex items-center justify-between py-3 text-sm">
                  <div>
                    <p className="font-medium">{e.description || e.merchant || "Expense"}</p>
                    <p className="text-muted">{e.expense_date}</p>
                  </div>
                  <p className="font-semibold text-danger">-{money(e.amount)}</p>
                </li>
              ))}
            </ul>
          ) : (
            <EmptyState title="No expenses yet" body="Record your first expense to see activity here." />
          )}
        </Panel>

        <Panel>
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-2xl font-semibold tracking-tight text-white">Savings Goals</h2>
            <Link to="/app/goals" className="text-sm font-semibold text-leaf">
              Manage
            </Link>
          </div>
          {goals.length ? (
            <ul className="space-y-4">
              {goals.map((g) => (
                <li key={g.id}>
                  <div className="mb-1 flex justify-between text-sm">
                    <span className="font-medium">{g.name}</span>
                    <span>{g.completion_percentage}%</span>
                  </div>
                  <div className="h-2 rounded-full bg-stone/50">
                    <div
                      className="h-2 rounded-full bg-mint"
                      style={{ width: `${Math.min(100, g.completion_percentage)}%` }}
                    />
                  </div>
                </li>
              ))}
            </ul>
          ) : (
            <EmptyState title="No active goals" body="Create a goal like Emergency Fund or Vacation." />
          )}
        </Panel>
      </div>
    </div>
  );
}
