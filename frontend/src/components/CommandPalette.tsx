import { useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  BarChart3,
  FileText,
  LayoutDashboard,
  Plus,
  Search,
  Sparkles,
  Target,
  WalletCards,
  X,
} from "lucide-react";

type CommandPaletteProps = {
  open: boolean;
  onClose: () => void;
  onAddTransaction: () => void;
};

const commands = [
  { label: "Dashboard", description: "View your financial overview", icon: LayoutDashboard, to: "/app" },
  { label: "Transactions", description: "Browse income and expenses", icon: WalletCards, to: "/app/transactions" },
  { label: "Analytics", description: "Explore spending trends", icon: BarChart3, to: "/app/analytics" },
  { label: "Goals", description: "Track your savings goals", icon: Target, to: "/app/goals" },
  { label: "AI Coach", description: "Ask for a money recommendation", icon: Sparkles, to: "/app/ai" },
  { label: "Reports", description: "Create and download reports", icon: FileText, to: "/app/reports" },
];

export default function CommandPalette({ open, onClose, onAddTransaction }: CommandPaletteProps) {
  const navigate = useNavigate();
  const inputRef = useRef<HTMLInputElement>(null);
  const [query, setQuery] = useState("");

  useEffect(() => {
    if (!open) return;
    setQuery("");
    const id = window.setTimeout(() => inputRef.current?.focus(), 0);
    return () => window.clearTimeout(id);
  }, [open]);

  useEffect(() => {
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    if (open) window.addEventListener("keydown", closeOnEscape);
    return () => window.removeEventListener("keydown", closeOnEscape);
  }, [open, onClose]);

  const results = useMemo(() => {
    const value = query.trim().toLowerCase();
    return commands.filter((item) => !value || `${item.label} ${item.description}`.toLowerCase().includes(value));
  }, [query]);

  if (!open) return null;

  const openTransaction = () => {
    onClose();
    onAddTransaction();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center bg-slate-950/40 px-4 pt-[12vh] backdrop-blur-sm" onMouseDown={onClose}>
      <section className="card-shadow w-full max-w-xl overflow-hidden rounded-2xl border border-line bg-card" role="dialog" aria-modal="true" aria-label="Quick actions" onMouseDown={(event) => event.stopPropagation()}>
        <div className="flex items-center gap-3 border-b border-line px-4">
          <Search className="h-5 w-5 text-moss" />
          <input ref={inputRef} value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search pages and actions..." className="h-14 min-w-0 flex-1 bg-transparent text-sm font-medium text-ink outline-none placeholder:text-muted" />
          <button type="button" onClick={onClose} className="rounded-lg p-1.5 text-muted transition hover:bg-sand hover:text-ink" aria-label="Close quick actions"><X className="h-4 w-4" /></button>
        </div>
        <div className="p-2">
          <p className="px-2 py-2 text-[10px] font-bold uppercase tracking-[0.16em] text-muted">Quick actions</p>
          <button type="button" onClick={openTransaction} className="flex w-full items-center gap-3 rounded-xl bg-soft px-3 py-3 text-left transition hover:bg-[#4a3127]">
            <span className="grid h-9 w-9 place-items-center rounded-xl bg-moss text-white"><Plus className="h-4 w-4" /></span>
            <span><span className="block text-sm font-bold text-ink">Add transaction</span><span className="block text-xs text-muted">Record income or an expense</span></span>
          </button>
          <p className="px-2 pb-2 pt-4 text-[10px] font-bold uppercase tracking-[0.16em] text-muted">Navigate</p>
          <div className="max-h-[40vh] overflow-y-auto">
            {results.map((item) => {
              const Icon = item.icon;
              return <button key={item.to} type="button" onClick={() => { navigate(item.to); onClose(); }} className="flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-left transition hover:bg-sand">
                <span className="grid h-9 w-9 place-items-center rounded-xl bg-cream text-muted"><Icon className="h-4 w-4" /></span>
                <span><span className="block text-sm font-semibold text-ink">{item.label}</span><span className="block text-xs text-muted">{item.description}</span></span>
              </button>;
            })}
            {!results.length ? <p className="px-3 py-8 text-center text-sm text-muted">No matching pages found.</p> : null}
          </div>
        </div>
        <div className="flex justify-between border-t border-line bg-sand/60 px-4 py-2 text-[11px] text-muted"><span>Choose an action</span><span><kbd className="rounded border border-line bg-card px-1">Esc</kbd> to close</span></div>
      </section>
    </div>
  );
}
