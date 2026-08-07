import { useEffect, useRef, useState } from "react";
import { aiApi } from "../api/finsight";
import {
  type AiChatMessage,
  AI_CHAT_CHIPS,
  buildHistoryForApi,
  clearStoredChat,
  defaultWelcome,
  loadChat,
  newMessageId,
  saveChat,
} from "../lib/aiChat";
import { emitDataChanged } from "../lib/events";
import { apiErrorMessage } from "../lib/errors";
import { useAppSelector } from "../store";

type Options = {
  year?: number;
  month?: number;
  firstName?: string;
};

export function useAiChat(options: Options = {}) {
  const user = useAppSelector((s) => s.auth.user);
  const userId = user?.id;
  const firstName = options.firstName || user?.full_name?.split(" ")[0] || "there";

  const [messages, setMessages] = useState<AiChatMessage[]>(() => {
    const saved = loadChat(userId);
    return saved ?? [defaultWelcome(firstName)];
  });
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const chatContainerRef = useRef<HTMLDivElement>(null);
  const chatEndRef = useRef<HTMLDivElement>(null);
  const hydratedUser = useRef<number | string | null>(null);

  const scrollToLatest = () => {
    const container = chatContainerRef.current;
    if (container) {
      container.scrollTo({ top: container.scrollHeight, behavior: "smooth" });
      return;
    }
    chatEndRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  };

  // Reload when auth user becomes available / changes
  useEffect(() => {
    if (userId == null) return;
    if (hydratedUser.current === userId) return;
    hydratedUser.current = userId;
    const saved = loadChat(userId);
    setMessages(saved ?? [defaultWelcome(firstName)]);
  }, [userId, firstName]);

  useEffect(() => {
    if (userId == null) return;
    saveChat(userId, messages);
  }, [messages, userId]);

  // Keep newest user/AI message (and "Thinking…") visible after each update.
  useEffect(() => {
    let timeoutId = 0;
    const frame = requestAnimationFrame(() => {
      scrollToLatest();
      // Second pass after layout (suggestion chips / long AI replies).
      timeoutId = window.setTimeout(scrollToLatest, 50);
    });
    return () => {
      cancelAnimationFrame(frame);
      if (timeoutId) window.clearTimeout(timeoutId);
    };
  }, [messages, loading]);

  const lastAssistantIndex = (() => {
    for (let i = messages.length - 1; i >= 0; i -= 1) {
      if (messages[i].role === "assistant") return i;
    }
    return -1;
  })();

  const ask = async (q: string) => {
    const question = q.trim();
    if (!question || loading) return;

    const history = buildHistoryForApi(messages);
    setMessages((m) => [...m, { id: newMessageId(), role: "user", text: question }]);
    setInput("");
    setLoading(true);

    try {
      const res = await aiApi.ask(question, history, options.year, options.month);
      const recorded = (res.context_summary as { recorded_transaction?: { kind?: string } } | undefined)
        ?.recorded_transaction;
      if (recorded?.kind === "income" || recorded?.kind === "expense") {
        emitDataChanged({ kind: recorded.kind });
      }

      setMessages((m) => [
        ...m,
        {
          id: newMessageId(),
          role: "assistant",
          text: res.answer,
          suggestedActions: res.suggested_actions?.length
            ? res.suggested_actions
            : [...AI_CHAT_CHIPS],
        },
      ]);
    } catch (err: unknown) {
      const status = (err as { response?: { status?: number } })?.response?.status;
      let text = apiErrorMessage(
        err,
        "I couldn't reach the AI service. Make sure the backend is running on port 8000.",
      );
      if (status === 401) {
        text = "Your session expired. Please sign out and sign in again.";
      } else if (status === 422) {
        text = apiErrorMessage(
          err,
          "That message couldn't be processed. Try a shorter question, or clear chat and try again.",
        );
      }
      setMessages((m) => [...m, { id: newMessageId(), role: "assistant", text }]);
    } finally {
      setLoading(false);
    }
  };

  const clearChat = () => {
    if (loading) return;
    clearStoredChat(userId);
    setMessages([defaultWelcome(firstName)]);
    setInput("");
  };

  const canClear = messages.length > 1;

  return {
    messages,
    input,
    setInput,
    loading,
    ask,
    clearChat,
    canClear,
    chatContainerRef,
    chatEndRef,
    lastAssistantIndex,
    chips: AI_CHAT_CHIPS,
  };
}
