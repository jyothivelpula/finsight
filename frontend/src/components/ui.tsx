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
        <h1 className="font-display text-3xl text-ink md:text-4xl">{title}</h1>
        {subtitle ? <p className="mt-1 text-sm text-muted">{subtitle}</p> : null}
      </div>
      {action}
    </div>
  );
}

export function Panel({ children, className = "" }: PropsWithChildren<{ className?: string }>) {
  return (
    <section className={`card-shadow surface-hover rounded-2xl border border-line bg-card p-5 ${className}`}>
      {children}
    </section>
  );
}

export function Stat({
  label,
  value,
  hint,
  icon,
  tone = "purple",
}: {
  label: string;
  value: string;
  hint?: string;
  icon?: ReactNode;
  tone?: "purple" | "green" | "red" | "blue";
}) {
  const tones = {
    purple: "bg-soft text-moss",
    green: "bg-emerald-50 text-emerald-600",
    red: "bg-rose-50 text-rose-600",
    blue: "bg-sky-50 text-sky-600",
  };
  return (
    <Panel className="animate-rise">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-sm font-medium text-muted">{label}</p>
          <p className="mt-2 text-2xl font-bold tracking-tight text-ink md:text-3xl">{value}</p>
          {hint ? <p className="mt-2 text-xs font-medium text-muted">{hint}</p> : null}
        </div>
        {icon ? (
          <div className={`grid h-11 w-11 place-items-center rounded-xl ${tones[tone]}`}>{icon}</div>
        ) : null}
      </div>
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
      ? "bg-moss text-white hover:bg-leaf shadow-sm shadow-moss/25"
      : variant === "danger"
        ? "bg-danger/10 text-danger hover:bg-danger/20"
        : "bg-white text-ink hover:bg-sand border border-line";
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
      {label ? <span className="text-sm font-medium text-ink">{label}</span> : null}
      <input
        className={`w-full rounded-xl border border-line bg-white px-3 py-2.5 text-sm text-ink outline-none ring-moss/20 placeholder:text-muted/60 focus:border-moss focus:ring-2 ${className}`}
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
      {label ? <span className="text-sm font-medium text-ink">{label}</span> : null}
      <select
        className={`w-full rounded-xl border border-line bg-white px-3 py-2.5 text-sm text-ink outline-none ring-moss/20 focus:border-moss focus:ring-2 ${className}`}
        {...props}
      >
        {children}
      </select>
    </label>
  );
}

export function EmptyState({ title, body }: { title: string; body: string }) {
  return (
    <div className="rounded-2xl border border-dashed border-line bg-sand/60 px-6 py-10 text-center">
      <p className="text-lg font-semibold tracking-tight text-ink">{title}</p>
      <p className="mt-2 text-sm text-muted">{body}</p>
    </div>
  );
}

export function StatusPill({ status }: { status: string }) {
  const tone =
    status === "exceeded"
      ? "bg-rose-50 text-rose-600"
      : status === "warning"
        ? "bg-amber-50 text-amber-700"
        : "bg-emerald-50 text-emerald-700";
  return (
    <span className={`rounded-full px-2.5 py-1 text-xs font-semibold capitalize ${tone}`}>
      {status.replace("_", " ")}
    </span>
  );
}
