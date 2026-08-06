import { useEffect, useRef, useState, type FormEvent } from "react";
import { Bot, Eraser, Send } from "lucide-react";
import { aiApi } from "../api/finsight";
import { Button, Input, PageHeader, Panel } from "../components/ui";
import { apiErrorMessage } from "../lib/errors";

interface Message {
  role: "user" | "assistant";
  text: string;
  suggestedActions?: string[];
}

const WELCOME: Message = {
  role: "assistant",
  text:
    "Hi — I'm FinSight AI.\n" +
    "Chat naturally, or ask about income, expenses, budgets, savings, goals, or analytics.",
  suggestedActions: [
    "How am I doing financially this month?",
    "Where did I spend the most?",
    "How much have I saved?",
  ],
};

export default function AIPage() {
  const [question, setQuestion] = useState("");
  const [loading, setLoading] = useState(false);
  const [messages, setMessages] = useState<Message[]>([WELCOME]);
  const chatEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages, loading]);

  const lastAssistantIndex = (() => {
    for (let i = messages.length - 1; i >= 0; i -= 1) {
      if (messages[i].role === "assistant") return i;
    }
    return -1;
  })();

  const ask = async (q: string) => {
    if (!q.trim() || loading) return;
    const history = messages
      .filter((m) => m.text)
      .slice(-8)
      .map((m) => ({ role: m.role, content: m.text }));
    setMessages((m) => [...m, { role: "user", text: q }]);
    setQuestion("");
    setLoading(true);
    try {
      const res = await aiApi.ask(q, history);
      setMessages((m) => [
        ...m,
        {
          role: "assistant",
          text: res.answer,
          suggestedActions: res.suggested_actions || [],
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
        text = apiErrorMessage(err, "Please enter a valid question and try again.");
      }
      setMessages((m) => [...m, { role: "assistant", text }]);
    } finally {
      setLoading(false);
    }
  };

  const onSubmit = (e: FormEvent) => {
    e.preventDefault();
    ask(question);
  };

  const clearChat = () => {
    if (loading) return;
    setMessages([WELCOME]);
    setQuestion("");
  };

  const canClear = messages.length > 1 || messages[0]?.text !== WELCOME.text;

  return (
    <div>
      <PageHeader
        title="Ask FinSight"
        subtitle="Your AI Coach — analyze, plan, and improve your finances"
      />
      <Panel className="mx-auto max-w-3xl">
        <div className="mb-4 flex items-center justify-between gap-3">
          <div className="flex items-center gap-2 text-ink">
            <Bot className="h-5 w-5 text-moss" />
            <h2 className="text-2xl font-semibold tracking-tight text-ink">AI Coach</h2>
          </div>
          <Button
            type="button"
            variant="ghost"
            onClick={clearChat}
            disabled={loading || !canClear}
            className="shrink-0"
          >
            <Eraser className="h-4 w-4" /> Clear chat
          </Button>
        </div>

        <div className="max-h-[480px] space-y-3 overflow-y-auto rounded-2xl border border-line bg-sand/50 p-4">
          {messages.map((m, i) => (
            <div key={i} className={m.role === "user" ? "flex justify-end" : "space-y-2"}>
              <div
                className={`max-w-[90%] whitespace-pre-wrap rounded-2xl px-4 py-3 text-sm leading-relaxed ${
                  m.role === "user"
                    ? "bg-moss text-white"
                    : "border border-line bg-card text-ink"
                }`}
              >
                {m.text}
              </div>
              {m.role === "assistant" &&
              i === lastAssistantIndex &&
              !loading &&
              m.suggestedActions?.length ? (
                <div className="max-w-[90%] flex flex-wrap gap-2">
                  {m.suggestedActions.map((action) => (
                    <button
                      key={action}
                      type="button"
                      onClick={() => ask(action)}
                      className="rounded-full border border-moss/20 bg-white px-3 py-1.5 text-xs font-medium text-moss hover:bg-soft"
                    >
                      {action}
                    </button>
                  ))}
                </div>
              ) : null}
            </div>
          ))}
          {loading ? <p className="text-sm text-muted">Thinking…</p> : null}
          <div ref={chatEndRef} />
        </div>

        <form onSubmit={onSubmit} className="mt-4 flex gap-2">
          <Input
            placeholder="Say hi, or ask about income, expenses, budgets…"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            className="flex-1"
          />
          <Button type="submit" disabled={loading}>
            <Send className="h-4 w-4" /> Ask
          </Button>
        </form>
      </Panel>
    </div>
  );
}
