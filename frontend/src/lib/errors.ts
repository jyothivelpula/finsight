export function apiErrorMessage(err: unknown, fallback: string): string {
  const detail = (err as { response?: { data?: { detail?: unknown } } })?.response?.data
    ?.detail;

  if (typeof detail === "string") return detail;

  if (Array.isArray(detail)) {
    return detail
      .map((item) => {
        if (typeof item === "string") return item;
        if (item && typeof item === "object" && "msg" in item) {
          return String((item as { msg: string }).msg);
        }
        return null;
      })
      .filter(Boolean)
      .join(". ");
  }

  if (err && typeof err === "object" && "message" in err) {
    const message = String((err as { message: string }).message);
    if (message.toLowerCase().includes("network")) {
      return "Cannot reach the server. Make sure the backend is running on port 8000.";
    }
  }

  return fallback;
}
