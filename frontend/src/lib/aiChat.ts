export type AiChatRole = "user" | "assistant";

export type AiChatMessage = {
  id: string;
  role: AiChatRole;
  text: string;
  suggestedActions?: string[];
};

export const AI_CHAT_CHIPS = [
  "How am I doing financially this month?",
  "Where did I spend the most?",
  "How much have I saved?",
];

const STORAGE_PREFIX = "finsight_ai_chat_v1_";
/** Keep under API max_length=12 and leave headroom. */
export const MAX_HISTORY_TURNS = 10;

export function newMessageId(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return crypto.randomUUID();
  }
  return `m_${Date.now()}_${Math.random().toString(36).slice(2, 9)}`;
}

export function defaultWelcome(firstName?: string): AiChatMessage {
  const name = firstName?.trim() || "there";
  return {
    id: newMessageId(),
    role: "assistant",
    text:
      `Hi ${name}! I'm FinSight AI.\n` +
      "Chat naturally, or tell me about income/expenses (e.g. “I spent ₹500 on food”) and I’ll log them. " +
      "You can also ask about budgets, savings, goals, or analytics.",
    suggestedActions: [...AI_CHAT_CHIPS],
  };
}

function storageKey(userId: number | string) {
  return `${STORAGE_PREFIX}${userId}`;
}

export function loadChat(userId: number | string | undefined | null): AiChatMessage[] | null {
  if (userId == null) return null;
  try {
    const raw = localStorage.getItem(storageKey(userId));
    if (!raw) return null;
    const parsed = JSON.parse(raw) as AiChatMessage[];
    if (!Array.isArray(parsed) || parsed.length === 0) return null;
    return parsed.map((m) => ({
      id: m.id || newMessageId(),
      role: m.role === "user" ? "user" : "assistant",
      text: String(m.text || ""),
      suggestedActions: m.suggestedActions,
    }));
  } catch {
    return null;
  }
}

export function saveChat(userId: number | string | undefined | null, messages: AiChatMessage[]) {
  if (userId == null) return;
  try {
    localStorage.setItem(storageKey(userId), JSON.stringify(messages));
  } catch {
    // ignore quota / private mode
  }
}

export function clearStoredChat(userId: number | string | undefined | null) {
  if (userId == null) return;
  try {
    localStorage.removeItem(storageKey(userId));
  } catch {
    // ignore
  }
}

/** Build API history: skip welcome-only opener, cap length, map to role/content. */
export function buildHistoryForApi(messages: AiChatMessage[]): { role: AiChatRole; content: string }[] {
  const real = messages.filter((m, index) => {
    if (!m.text?.trim()) return false;
    // Drop the initial welcome assistant bubble so it does not burn history slots.
    if (index === 0 && m.role === "assistant") return false;
    return true;
  });
  return real.slice(-MAX_HISTORY_TURNS).map((m) => ({
    role: m.role,
    content: m.text.slice(0, 2000),
  }));
}
