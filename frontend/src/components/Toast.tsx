import { CheckCircle2, X } from "lucide-react";

export type ToastState = {
  message: string;
  tone?: "success" | "error";
} | null;

export default function Toast({
  toast,
  onClose,
}: {
  toast: ToastState;
  onClose: () => void;
}) {
  if (!toast) return null;

  const success = toast.tone !== "error";

  return (
    <div className="pointer-events-none fixed inset-x-0 bottom-6 z-[70] flex justify-center px-4">
      <div
        className={`pointer-events-auto flex max-w-md items-start gap-3 rounded-2xl border px-4 py-3 shadow-lg ${
          success
            ? "border-emerald-200 bg-white text-ink"
            : "border-rose-200 bg-white text-ink"
        }`}
        role="status"
      >
        <CheckCircle2
          className={`mt-0.5 h-5 w-5 shrink-0 ${success ? "text-emerald-600" : "text-rose-600"}`}
        />
        <p className="flex-1 text-sm font-medium leading-relaxed">{toast.message}</p>
        <button
          type="button"
          onClick={onClose}
          className="rounded-lg p-1 text-muted hover:bg-sand hover:text-ink"
          aria-label="Dismiss"
        >
          <X className="h-4 w-4" />
        </button>
      </div>
    </div>
  );
}
