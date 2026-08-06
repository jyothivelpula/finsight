import { useEffect, useState } from "react";
import { NavLink, Outlet } from "react-router-dom";
import {
  Activity,
  ArrowDownCircle,
  ArrowLeftRight,
  ArrowUpCircle,
  Bell,
  Calendar,
  CircleHelp,
  FileText,
  LayoutDashboard,
  LogOut,
  Plus,
  Settings,
  Sparkles,
  Target,
  Wallet,
} from "lucide-react";
import AddTransactionModal from "./AddTransactionModal";
import BrandLogo from "./BrandLogo";
import Toast, { type ToastState } from "./Toast";
import { logout } from "../store/authSlice";
import { useAppDispatch, useAppSelector } from "../store";
import { currentYearMonth } from "../lib/format";

type NavItem = {
  to: string;
  end?: boolean;
  label: string;
  icon: typeof LayoutDashboard;
  iconClass: string;
};

const primaryLinks: NavItem[] = [
  { to: "/app", end: true, label: "Dashboard", icon: LayoutDashboard, iconClass: "text-moss" },
  { to: "/app/expenses", label: "Transactions", icon: ArrowLeftRight, iconClass: "text-slate-500" },
];

const manageLinks: NavItem[] = [
  { to: "/app/income", label: "Income", icon: ArrowUpCircle, iconClass: "text-emerald-500" },
  { to: "/app/expenses", label: "Expenses", icon: ArrowDownCircle, iconClass: "text-rose-500" },
  { to: "/app/budgets", label: "Budgets", icon: Wallet, iconClass: "text-sky-500" },
  { to: "/app/goals", label: "Goals", icon: Target, iconClass: "text-rose-500" },
];

const insightLinks: NavItem[] = [
  { to: "/app/analytics", label: "Analytics", icon: Activity, iconClass: "text-blue-500" },
  { to: "/app/ai", label: "AI Coach", icon: Sparkles, iconClass: "text-violet-500" },
  { to: "/app/reports", label: "Reports", icon: FileText, iconClass: "text-indigo-500" },
];

function NavRow({ item }: { item: NavItem }) {
  const Icon = item.icon;

  return (
    <NavLink
      to={item.to}
      end={item.end}
      className={({ isActive }) =>
        `flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition ${
          isActive
            ? "bg-moss text-white shadow-sm shadow-moss/25"
            : "text-slate-600 hover:bg-sand hover:text-ink"
        }`
      }
    >
      {({ isActive }) => (
        <>
          <Icon className={`h-4 w-4 ${isActive ? "text-white" : item.iconClass}`} />
          {item.label}
        </>
      )}
    </NavLink>
  );
}

export default function AppLayout() {
  const user = useAppSelector((s) => s.auth.user);
  const dispatch = useAppDispatch();
  const { year, month } = currentYearMonth();
  const monthLabel = new Date(year, month - 1, 1).toLocaleString("en-IN", {
    month: "long",
    year: "numeric",
  });
  const firstName = user?.full_name?.split(" ")[0] || "there";
  const initials =
    user?.full_name
      ?.split(" ")
      .map((p) => p[0])
      .slice(0, 2)
      .join("")
      .toUpperCase() || "U";

  const [txOpen, setTxOpen] = useState(false);
  const [toast, setToast] = useState<ToastState>(null);

  useEffect(() => {
    if (!toast) return;
    const id = window.setTimeout(() => setToast(null), 3200);
    return () => window.clearTimeout(id);
  }, [toast]);

  return (
    <div className="app-bg min-h-screen lg:grid lg:grid-cols-[260px_1fr]">
      <aside className="w-full border-b border-line bg-white lg:sticky lg:top-0 lg:h-screen lg:w-[260px] lg:overflow-y-auto lg:border-b-0 lg:border-r">
        <div className="px-5 pb-2 pt-5">
          <BrandLogo imgClassName="h-9 w-auto max-w-[170px]" />
          <p className="mt-1 text-[11px] font-medium text-muted">Your Financial OS</p>
        </div>

        <nav className="flex flex-col gap-5 px-3 py-3">
          <div className="flex flex-col gap-0.5">
            {primaryLinks.map((item) => (
              <NavRow key={item.label} item={item} />
            ))}
          </div>

          <div className="flex flex-col gap-0.5">
            <p className="px-3 pb-1 text-[10px] font-semibold uppercase tracking-[0.16em] text-slate-400">
              Manage Money
            </p>
            {manageLinks.map((item) => (
              <NavRow key={item.label} item={item} />
            ))}
          </div>

          <div className="flex flex-col gap-0.5">
            <p className="px-3 pb-1 text-[10px] font-semibold uppercase tracking-[0.16em] text-slate-400">
              Insights
            </p>
            {insightLinks.map((item) => (
              <NavRow key={item.label} item={item} />
            ))}
          </div>

          <div className="flex flex-col gap-0.5">
            <NavRow
              item={{
                to: "/app/settings",
                label: "Settings",
                icon: Settings,
                iconClass: "text-slate-400",
              }}
            />
            <NavRow
              item={{
                to: "/app/help",
                label: "Help & Support",
                icon: CircleHelp,
                iconClass: "text-slate-400",
              }}
            />
            <button
              type="button"
              onClick={() => dispatch(logout())}
              className="flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium text-rose-500 hover:bg-rose-50"
            >
              <LogOut className="h-4 w-4" /> Sign Out
            </button>
          </div>
        </nav>
      </aside>

      <div className="min-w-0">
        <header className="sticky top-0 z-20 flex flex-wrap items-center justify-between gap-3 border-b border-line bg-white/90 px-4 py-3 backdrop-blur md:px-7">
          <div className="hidden sm:block">
            <p className="text-sm text-muted">Welcome back,</p>
            <p className="font-semibold text-ink">{firstName}</p>
          </div>
          <div className="flex flex-wrap items-center gap-2 sm:gap-3">
            <div className="inline-flex items-center gap-2 rounded-xl border border-line bg-sand px-3 py-2 text-sm font-medium text-ink">
              <Calendar className="h-4 w-4 text-moss" />
              {monthLabel}
            </div>
            <button
              type="button"
              onClick={() => setTxOpen(true)}
              className="inline-flex items-center gap-2 rounded-xl bg-moss px-4 py-2.5 text-sm font-semibold text-white shadow-sm shadow-moss/25"
            >
              <Plus className="h-4 w-4" /> Add Transaction
            </button>
            <button
              type="button"
              className="relative grid h-10 w-10 place-items-center rounded-xl border border-line bg-white text-muted hover:text-ink"
              aria-label="Notifications"
            >
              <Bell className="h-4 w-4" />
              <span className="absolute right-2 top-2 h-2 w-2 rounded-full bg-danger" />
            </button>
            <div className="flex items-center gap-2 rounded-xl border border-line bg-white px-2.5 py-1.5">
              <div className="grid h-9 w-9 place-items-center rounded-full bg-soft text-sm font-bold text-moss">
                {initials}
              </div>
              <div className="hidden pr-1 sm:block">
                <p className="text-sm font-semibold leading-tight text-ink">{user?.full_name}</p>
              </div>
            </div>
          </div>
        </header>

        <main className="px-4 py-5 md:px-7 md:py-6">
          <Outlet />
        </main>
      </div>

      <AddTransactionModal
        open={txOpen}
        onClose={() => setTxOpen(false)}
        onSuccess={(message) => setToast({ message, tone: "success" })}
      />
      <Toast toast={toast} onClose={() => setToast(null)} />
    </div>
  );
}
