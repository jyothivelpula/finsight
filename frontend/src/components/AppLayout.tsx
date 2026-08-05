import { NavLink, Outlet } from "react-router-dom";
import {
  BarChart3,
  Bot,
  FileText,
  LayoutDashboard,
  LogOut,
  Target,
  Wallet,
  ArrowDownCircle,
  ArrowUpCircle,
} from "lucide-react";
import { logout } from "../store/authSlice";
import { useAppDispatch, useAppSelector } from "../store";

const links = [
  { to: "/app", end: true, label: "Dashboard", icon: LayoutDashboard },
  { to: "/app/income", label: "Income", icon: ArrowUpCircle },
  { to: "/app/expenses", label: "Expenses", icon: ArrowDownCircle },
  { to: "/app/budgets", label: "Budgets", icon: Wallet },
  { to: "/app/goals", label: "Goals", icon: Target },
  { to: "/app/analytics", label: "Analytics", icon: BarChart3 },
  { to: "/app/ai", label: "AI Assistant", icon: Bot },
  { to: "/app/reports", label: "Reports", icon: FileText },
];

export default function AppLayout() {
  const user = useAppSelector((s) => s.auth.user);
  const dispatch = useAppDispatch();

  return (
    <div className="app-bg min-h-screen lg:grid lg:grid-cols-[248px_1fr]">
      <aside className="border-b border-line bg-[#0a0e0c] text-ink lg:min-h-screen lg:border-b-0 lg:border-r">
        <div className="flex items-center gap-3 px-5 py-5">
          <div className="grid h-9 w-9 place-items-center rounded-full bg-moss text-sm font-bold text-black">
            F
          </div>
          <div>
            <p className="text-lg font-semibold leading-none tracking-tight">FinSight</p>
            <p className="mt-1 text-[11px] uppercase tracking-[0.16em] text-muted">Finance OS</p>
          </div>
        </div>
        <nav className="flex gap-1 overflow-x-auto px-3 pb-3 lg:flex-col lg:overflow-visible lg:px-3 lg:pb-6">
          {links.map(({ to, label, icon: Icon, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              className={({ isActive }) =>
                `flex items-center gap-2 whitespace-nowrap rounded-xl px-3 py-2.5 text-sm transition ${
                  isActive
                    ? "bg-moss/15 text-leaf"
                    : "text-muted hover:bg-white/5 hover:text-white"
                }`
              }
            >
              <Icon className="h-4 w-4" />
              {label}
            </NavLink>
          ))}
        </nav>
        <div className="hidden border-t border-line px-4 py-4 lg:block">
          <p className="truncate text-sm font-medium text-white">{user?.full_name}</p>
          <p className="truncate text-xs text-muted">{user?.email}</p>
          <button
            onClick={() => dispatch(logout())}
            className="mt-3 inline-flex items-center gap-2 text-sm text-muted hover:text-leaf"
          >
            <LogOut className="h-4 w-4" /> Sign out
          </button>
        </div>
      </aside>

      <main className="px-4 py-6 md:px-8 md:py-8">
        <Outlet />
      </main>
    </div>
  );
}
