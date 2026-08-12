import { useEffect, useMemo, useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import {
  AlertTriangle,
  ArrowRight,
  CheckCircle2,
  Eraser,
  IndianRupee,
  Send,
  Target,
} from "lucide-react";
import {
  Cell,
  CartesianGrid,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { analyticsApi, financeApi } from "../api/finsight";
import { EmptyState, Panel } from "../components/ui";
import { useAiChat } from "../hooks/useAiChat";
import { onDataChanged } from "../lib/events";
import { currentYearMonth, money, moneyCompact } from "../lib/format";
import type { AnalyticsDashboard, Goal, Income } from "../types";
import { useAppSelector } from "../store";

function greetingForNow() {
  const h = new Date().getHours();
  if (h < 12) return "Good Morning";
  if (h < 17) return "Good Afternoon";
  return "Good Evening";
}

function scoreTone(status: string) {
  const s = status.toLowerCase();
  if (s === "excellent" || s === "good") return "text-emerald-600";
  if (s === "fair") return "text-amber-600";
  if (s === "no data") return "text-muted";
  return "text-rose-600";
}

function barColor(score: number) {
  if (score >= 80) return "bg-emerald-500";
  if (score >= 65) return "bg-lime-500";
  if (score >= 50) return "bg-amber-400";
  return "bg-orange-500";
}

function monthEndLabel(year: number, month: number) {
  const last = new Date(year, month, 0);
  return last.toLocaleString("en-IN", { month: "short", day: "numeric", year: "numeric" });
}

export default function Dashboard() {
  const user = useAppSelector((s) => s.auth.user);
  const { year, month } = currentYearMonth();
  const firstName = user?.full_name?.split(" ")[0] || "there";

  const [data, setData] = useState<AnalyticsDashboard | null>(null);
  const [goals, setGoals] = useState<Goal[]>([]);
  const [incomes, setIncomes] = useState<Income[]>([]);
  const {
    messages: chatMessages,
    input: chatInput,
    setInput: setChatInput,
    loading: chatLoading,
    ask: askChat,
    clearChat,
    canClear,
    chatContainerRef,
    chatEndRef,
    chips: AI_CHIPS,
  } = useAiChat({ year, month, firstName });

  const loadDashboard = () => {
    Promise.all([
      analyticsApi.dashboard(year, month),
      financeApi.goals(),
      financeApi.incomes({ year, month }),
    ]).then(([dash, g, inc]) => {
      setData(dash);
      setGoals(g.filter((x) => x.status === "active").slice(0, 3));
      setIncomes(inc);
    });
  };

  useEffect(() => {
    loadDashboard();
  }, [year, month]);

  useEffect(() => onDataChanged(() => {
    loadDashboard();
  }), [year, month]);

  const healthBars = useMemo(() => {
    if (!data) return [];
    // Components are 0–25; show as 0–100 for the bars.
    const to100 = (v: number | undefined) => Math.round(((v ?? 0) / 25) * 100);
    return [
      { label: "Spending", score: to100(data.spending_score) },
      { label: "Savings", score: to100(data.savings_score) },
      { label: "Budget", score: to100(data.budget_score) },
      { label: "Goals", score: to100(data.goals_score) },
    ];
  }, [data]);

  if (!data) {
    return <p className="text-muted">Loading dashboard…</p>;
  }

  // Prefer explicit API health fields; fall back to summary only if missing.
  const hasHealthData = data.health_has_data !== false && (
    Number(data.summary.total_income) > 0
    || Number(data.summary.total_expenses) > 0
    || (data.budget_analytics?.length ?? 0) > 0
    || (data.goal_progress?.length ?? 0) > 0
  );
  const score = hasHealthData
    ? Number(data.health_score ?? data.summary.financial_health_score ?? 0)
    : 0;
  const healthStatus = hasHealthData
    ? (data.health_status || "Fair")
    : "No Data";
  const income = Number(data.summary.total_income || 0);
  const expenses = Number(data.summary.total_expenses || 0);
  const savings = Number(data.summary.net_savings || 0);
  const goalContrib = goals.reduce((sum, g) => sum + Number(g.current_amount || 0), 0) * 0.05;
  const planned = expenses * 0.15;
  const safeToSpend = Math.max(0, savings - planned - goalContrib);
  const canSpendSafely = safeToSpend > 0 && score >= 55;

  const gaugeData = [
    { name: "score", value: Math.min(100, Math.max(0, score)) },
    { name: "rest", value: Math.max(0, 100 - score) },
  ];

  const reportedTrend = data.monthly_trends.slice(-6).map((p) => ({
    period: p.period.slice(5),
    income: Number(p.income),
    expenses: Number(p.expenses),
    savings: Number(p.savings),
  }));
  const trend = reportedTrend.length
    ? reportedTrend
    : Array.from({ length: 5 }, (_, index) => {
        const date = new Date(year, month - 5 + index, 1);
        return {
          period: date.toLocaleString("en-IN", { month: "2-digit" }),
          income: 0,
          expenses: 0,
          savings: 0,
        };
      });

  const attentionItems = [
    ...data.insights.slice(0, 2).map((insight, i) => ({
      id: `insight-${i}`,
      icon: "alert" as const,
      title: insight,
      actions: [
        { label: "Analyze", to: "/app/analytics" },
        { label: "Set Limit", to: "/app/budgets" },
      ],
    })),
    ...(goals[0]
      ? [
          {
            id: "goal",
            icon: "goal" as const,
            title: `${goals[0].name} is ${goals[0].completion_percentage}% complete.`,
            actions: [{ label: "View Goal", to: "/app/goals" }],
          },
        ]
      : []),
    ...(incomes[0]
      ? [
          {
            id: "income",
            icon: "income" as const,
            title: `${incomes[0].source} received — ${money(incomes[0].amount)} credited.`,
            actions: [{ label: "View Transaction", to: "/app/income" }],
          },
        ]
      : []),
  ].slice(0, 3);

  const positionLine =
    !hasHealthData
      ? "Add income or expenses to unlock your Financial Health Score."
      : score >= 70
        ? "You're in a strong financial position."
        : score >= 50
          ? "You're on track — a few tweaks can strengthen your position."
          : "Let's tighten spending and rebuild your financial cushion.";

  const latestSuggestions =
    [...chatMessages].reverse().find((m) => m.role === "assistant")?.suggestedActions || AI_CHIPS;

  return (
    <div className="space-y-5">
      <div className="relative overflow-hidden rounded-3xl border border-[#3a302d] bg-gradient-to-br from-[#29262a] via-[#24252b] to-[#35241f] px-5 py-6 card-shadow md:px-7">
        <div className="absolute -right-12 -top-16 h-48 w-48 rounded-full bg-orange-400/10 blur-3xl" />
        <div className="relative flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
          <div>
            <p className="text-xs font-bold uppercase tracking-[0.18em] text-moss">Financial overview</p>
            <h1 className="mt-2 font-display text-3xl text-ink md:text-4xl">
              {greetingForNow()}, {firstName}!
            </h1>
            <p className="mt-2 max-w-2xl text-sm text-muted">{positionLine}</p>
          </div>
          <div className="flex shrink-0 gap-2">
            <Link to="/app/analytics" className="rounded-xl border border-line bg-sand px-3 py-2 text-xs font-bold text-moss transition hover:border-moss/30 hover:bg-soft">View insights</Link>
            <Link to="/app/goals" className="rounded-xl bg-moss px-3 py-2 text-xs font-bold text-white transition hover:bg-leaf">Your goals</Link>
          </div>
        </div>
      </div>

      <div className="grid gap-4 xl:grid-cols-3">
        <Panel className="animate-rise">
          <h2 className="text-base font-bold text-ink">Financial Health</h2>
          <div className="mt-3 flex flex-col gap-4 sm:flex-row sm:items-center">
            <div className="relative mx-auto h-36 w-36 shrink-0">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart key={`health-${score}-${healthStatus}`}>
                  <Pie
                    data={gaugeData}
                    dataKey="value"
                    startAngle={90}
                    endAngle={-270}
                    innerRadius={48}
                    outerRadius={64}
                    stroke="none"
                    isAnimationActive={false}
                  >
                    <Cell fill={hasHealthData ? "#6366f1" : "#cbd5e1"} />
                    <Cell fill="#e2e8f0" />
                  </Pie>
                </PieChart>
              </ResponsiveContainer>
              <div className="pointer-events-none absolute inset-0 grid place-items-center text-center">
                <div>
                  <p className="text-xl font-bold text-ink">
                    {hasHealthData ? `${Math.round(score)}/100` : "—"}
                  </p>
                  <p className={`text-xs font-bold uppercase ${scoreTone(healthStatus)}`}>
                    {healthStatus}
                  </p>
                </div>
              </div>
            </div>
            <ul className="flex-1 space-y-3">
              {healthBars.map((bar) => (
                <li key={bar.label}>
                  <div className="mb-1 flex justify-between text-xs">
                    <span className="font-medium text-ink">{bar.label}</span>
                    <span className="text-muted">
                      {bar.score}/100
                    </span>
                  </div>
                  <div className="h-2 rounded-full bg-cream">
                    <div
                      className={`h-2 rounded-full ${barColor(bar.score)}`}
                      style={{ width: `${Math.min(100, bar.score)}%` }}
                    />
                  </div>
                </li>
              ))}
            </ul>
          </div>
          <Link to="/app/analytics" className="mt-4 inline-flex items-center gap-1 text-sm font-semibold text-moss">
            View full health report <ArrowRight className="h-3.5 w-3.5" />
          </Link>
        </Panel>

        <Panel className="animate-rise">
          <h2 className="text-base font-bold text-ink">Safe to Spend</h2>
          <p className="mt-3 text-3xl font-bold tracking-tight text-emerald-600">
            {money(safeToSpend)}
          </p>
          <p className="mt-1 text-sm text-muted">until {monthEndLabel(year, month)}</p>
          <ul className="mt-4 space-y-2 text-sm">
            <li className="flex justify-between">
              <span className="text-muted">Income left</span>
              <span className="font-semibold text-ink">{money(savings)}</span>
            </li>
            <li className="flex justify-between">
              <span className="text-muted">Goal contributions</span>
              <span className="font-semibold text-ink">{money(goalContrib)}</span>
            </li>
            <li className="flex justify-between">
              <span className="text-muted">Planned spending</span>
              <span className="font-semibold text-ink">{money(planned)}</span>
            </li>
          </ul>
          <div
            className={`mt-4 rounded-xl px-3 py-2.5 text-sm font-medium ${
              canSpendSafely
                ? "bg-emerald-50 text-emerald-700"
                : "bg-amber-50 text-amber-700"
            }`}
          >
            {canSpendSafely
              ? "✅ You can spend safely. Keep going!"
              : "⚠️ Keep spending tight until your cushion improves."}
          </div>
        </Panel>

        <Panel className="animate-rise">
          <h2 className="text-base font-bold text-ink">Your Money This Month</h2>
          <div className="mt-4 grid grid-cols-3 gap-2">
            <div>
              <p className="text-xs text-muted">Income</p>
              <p className="mt-1 text-lg font-bold text-emerald-600">{moneyCompact(income)}</p>
            </div>
            <div>
              <p className="text-xs text-muted">Expenses</p>
              <p className="mt-1 text-lg font-bold text-rose-600">{moneyCompact(expenses)}</p>
            </div>
            <div>
              <p className="text-xs text-muted">Savings</p>
              <p className="mt-1 text-lg font-bold text-blue-600">{moneyCompact(savings)}</p>
            </div>
          </div>
          <div className="mt-5 h-48 rounded-xl bg-[#1c1d22] px-1 pt-3">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={trend} margin={{ top: 12, right: 8, left: 8, bottom: 8 }}>
                <CartesianGrid vertical={false} stroke="#303138" strokeDasharray="3 4" />
                <XAxis dataKey="period" stroke="#9b9ca4" tickLine={{ stroke: "#8d8fff" }} axisLine={{ stroke: "#8d8fff", strokeWidth: 2 }} tick={{ fill: "#9b9ca4", fontSize: 11 }} />
                <YAxis hide domain={reportedTrend.length ? ["auto", "auto"] : [-1, 1]} />
                {reportedTrend.length ? <Tooltip contentStyle={{ background: "#292a30", border: "1px solid #44454c", borderRadius: 12, color: "#f4f4f5" }} labelStyle={{ color: "#a0a1a8" }} formatter={(v) => money(Number(v))} /> : null}
                {reportedTrend.length ? <>
                  <Line type="monotone" dataKey="income" name="Income" stroke="#00c48c" strokeWidth={2.5} dot={false} activeDot={{ r: 4, fill: "#00c48c" }} />
                  <Line type="monotone" dataKey="expenses" name="Expenses" stroke="#ff0058" strokeWidth={2.5} dot={false} activeDot={{ r: 4, fill: "#ff0058" }} />
                  <Line type="monotone" dataKey="savings" name="Savings" stroke="#2777ff" strokeWidth={2.5} dot={false} activeDot={{ r: 4, fill: "#2777ff" }} />
                </> : null}
              </LineChart>
            </ResponsiveContainer>
          </div>
          <Link to="/app/analytics" className="mt-2 inline-flex items-center gap-1 text-sm font-semibold text-moss">
            View interactive timeline <ArrowRight className="h-3.5 w-3.5" />
          </Link>
        </Panel>
      </div>

      <div className="grid gap-4 xl:grid-cols-2">
        <Panel>
          <h2 className="text-base font-bold text-ink">What Needs Your Attention?</h2>
          {attentionItems.length ? (
            <ul className="mt-4 space-y-3">
              {attentionItems.map((item) => (
                <li
                  key={item.id}
                  className="rounded-2xl border border-line bg-sand/60 px-3 py-3"
                >
                  <div className="flex items-start gap-3">
                    <div
                      className={`mt-0.5 grid h-9 w-9 shrink-0 place-items-center rounded-xl ${
                        item.icon === "goal"
                          ? "bg-emerald-50 text-emerald-600"
                          : item.icon === "income"
                            ? "bg-soft text-moss"
                            : "bg-amber-50 text-amber-600"
                      }`}
                    >
                      {item.icon === "goal" ? (
                        <Target className="h-4 w-4" />
                      ) : item.icon === "income" ? (
                        <IndianRupee className="h-4 w-4" />
                      ) : (
                        <AlertTriangle className="h-4 w-4" />
                      )}
                    </div>
                    <div className="min-w-0 flex-1">
                      <p className="text-sm font-medium text-ink">{item.title}</p>
                      <div className="mt-2 flex flex-wrap gap-2">
                        {item.actions.map((action) => (
                          <Link
                            key={action.label}
                            to={action.to}
                            className="rounded-lg border border-line bg-white px-2.5 py-1 text-xs font-semibold text-ink hover:border-moss/30 hover:text-moss"
                          >
                            {action.label}
                          </Link>
                        ))}
                      </div>
                    </div>
                  </div>
                </li>
              ))}
            </ul>
          ) : (
            <div className="mt-4 flex items-start gap-3 rounded-2xl bg-emerald-50 px-3 py-3 text-sm text-emerald-700">
              <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0" />
              Everything looks calm. Add more activity to unlock smarter alerts.
            </div>
          )}
        </Panel>

        <Panel className="flex flex-col overflow-hidden p-0">
          <div className="flex items-center justify-between border-b border-line px-5 py-4">
            <div>
              <h2 className="text-base font-bold text-ink">Ask FinSight</h2>
              <p className="text-xs font-medium text-moss">AI Coach</p>
            </div>
            <button
              type="button"
              onClick={clearChat}
              disabled={chatLoading || !canClear}
              className="inline-flex items-center gap-1.5 rounded-lg px-2.5 py-1.5 text-xs font-semibold text-muted hover:bg-sand hover:text-ink disabled:opacity-40"
              title="Clear chat"
            >
              <Eraser className="h-3.5 w-3.5" /> Clear
            </button>
          </div>

          <div
            ref={chatContainerRef}
            className="max-h-64 flex-1 space-y-3 overflow-y-auto px-4 py-4"
          >
            {chatMessages.map((m) => (
              <div
                key={m.id}
                className={`max-w-[92%] whitespace-pre-wrap rounded-2xl px-3 py-2 text-sm leading-relaxed ${
                  m.role === "user"
                    ? "ml-auto bg-moss text-white"
                    : "border border-line bg-sand/50 text-ink"
                }`}
              >
                {m.text}
              </div>
            ))}
            {chatLoading ? <p className="text-xs text-muted">Thinking…</p> : null}
            <div ref={chatEndRef} aria-hidden className="h-px w-full shrink-0" />
          </div>

          <div className="space-y-3 border-t border-line px-4 py-3">
            <div className="flex flex-col gap-2">
              {latestSuggestions.slice(0, 3).map((chip) => (
                <button
                  key={chip}
                  type="button"
                  disabled={chatLoading}
                  onClick={() => askChat(chip)}
                  className="flex items-center justify-between rounded-xl border border-line bg-white px-3 py-2 text-left text-xs font-medium text-ink hover:border-moss/40 hover:bg-soft disabled:opacity-50"
                >
                  <span>{chip}</span>
                  <ArrowRight className="h-3.5 w-3.5 text-moss" />
                </button>
              ))}
            </div>
            <form
              className="flex gap-2"
              onSubmit={(e: FormEvent) => {
                e.preventDefault();
                askChat(chatInput);
              }}
            >
              <input
                value={chatInput}
                onChange={(e) => setChatInput(e.target.value)}
                placeholder="Ask anything about your money…"
                className="w-full rounded-xl border border-line bg-sand/40 px-3 py-2.5 text-sm outline-none focus:border-moss focus:bg-white focus:ring-2 focus:ring-moss/20"
              />
              <button
                type="submit"
                disabled={chatLoading}
                className="grid h-11 w-11 shrink-0 place-items-center rounded-full bg-moss text-white shadow-sm shadow-moss/25 disabled:opacity-50"
              >
                <Send className="h-4 w-4" />
              </button>
            </form>
          </div>
        </Panel>
      </div>
    </div>
  );
}
