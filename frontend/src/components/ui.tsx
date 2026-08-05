import type {
  ButtonHTMLAttributes,
  InputHTMLAttributes,
  PropsWithChildren,
  ReactNode,
  SelectHTMLAttributes,
} from "react";

export function PageHeader({
  title,
  subtitle,
  action,
}: {
  title: string;
  subtitle?: string;
  action?: ReactNode;
}) {
  return (
    <div className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
      <div>
        <h1 className="text-3xl font-semibold tracking-tight text-white md:text-4xl">{title}</h1>
        {subtitle ? <p className="mt-1 text-sm text-muted">{subtitle}</p> : null}
      </div>
      {action}
    </div>
  );
}

export function Panel({ children, className = "" }: PropsWithChildren<{ className?: string }>) {
  return (
    <section
      className={`rounded-2xl border border-line bg-card/90 p-5 shadow-[0_10px_40px_rgba(0,0,0,0.25)] ${className}`}
    >
      {children}
    </section>
  );
}

export function Stat({
  label,
  value,
  hint,
}: {
  label: string;
  value: string;
  hint?: string;
}) {
  return (
    <Panel className="animate-rise">
      <p className="text-xs font-medium uppercase tracking-[0.14em] text-muted">{label}</p>
      <p className="mt-2 text-3xl font-semibold tracking-tight text-leaf">{value}</p>
      {hint ? <p className="mt-1 text-sm text-muted">{hint}</p> : null}
    </Panel>
  );
}

export function Button({
  variant = "primary",
  className = "",
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: "primary" | "ghost" | "danger" }) {
  const styles =
    variant === "primary"
      ? "bg-moss text-black hover:bg-leaf"
      : variant === "danger"
        ? "bg-danger/10 text-danger hover:bg-danger/20"
        : "bg-transparent text-ink hover:bg-white/5 border border-line";
  return (
    <button
      className={`inline-flex items-center justify-center gap-2 rounded-xl px-4 py-2.5 text-sm font-semibold transition disabled:opacity-50 ${styles} ${className}`}
      {...props}
    />
  );
}

export function Input({
  label,
  className = "",
  ...props
}: InputHTMLAttributes<HTMLInputElement> & { label?: string }) {
  return (
    <label className="block space-y-1.5">
      {label ? <span className="text-sm font-medium text-white/85">{label}</span> : null}
      <input
        className={`w-full rounded-xl border border-line bg-[#0d1210] px-3 py-2.5 text-sm text-white outline-none ring-moss/30 placeholder:text-muted/50 focus:border-moss/50 focus:ring-2 ${className}`}
        {...props}
      />
    </label>
  );
}

export function Select({
  label,
  children,
  className = "",
  ...props
}: SelectHTMLAttributes<HTMLSelectElement> & { label?: string }) {
  return (
    <label className="block space-y-1.5">
      {label ? <span className="text-sm font-medium text-white/85">{label}</span> : null}
      <select
        className={`w-full rounded-xl border border-line bg-[#0d1210] px-3 py-2.5 text-sm text-white outline-none ring-moss/30 focus:border-moss/50 focus:ring-2 ${className}`}
        {...props}
      >
        {children}
      </select>
    </label>
  );
}

export function EmptyState({ title, body }: { title: string; body: string }) {
  return (
    <div className="rounded-2xl border border-dashed border-line px-6 py-10 text-center">
      <p className="text-2xl font-semibold tracking-tight text-leaf">{title}</p>
      <p className="mt-2 text-sm text-muted">{body}</p>
    </div>
  );
}

export function StatusPill({ status }: { status: string }) {
  const tone =
    status === "exceeded" || status === "warning"
      ? status === "exceeded"
        ? "bg-danger/15 text-danger"
        : "bg-warn/15 text-warn"
      : "bg-moss/15 text-leaf";
  return (
    <span className={`rounded-full px-2.5 py-1 text-xs font-semibold capitalize ${tone}`}>
      {status.replace("_", " ")}
    </span>
  );
}
