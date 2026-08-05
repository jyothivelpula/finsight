import { useState, type FormEvent } from "react";
import { Bot, Send } from "lucide-react";
import { aiApi } from "../api/finsight";
import { Button, Input, PageHeader, Panel } from "../components/ui";
import { apiErrorMessage } from "../lib/errors";

const SUGGESTIONS = [
  "Where did I spend the most money?",
  "How can I save ₹10,000 next month?",
  "Which category exceeded my budget?",
  "What is affecting my financial health score?",
  "How much can I save if I reduce shopping by 20%?",
];

interface Message {
  role: "user" | "assistant";
  text: string;
}

export default function AIPage() {
  const [question, setQuestion] = useState("");
  const [loading, setLoading] = useState(false);
  const [messages, setMessages] = useState<Message[]>([
    {
      role: "assistant",
      text: "Hi — I'm your FinSight assistant. Tell me what you want to know about your money, and I'll look it up, calculate if needed, and answer clearly.",
    },
  ]);

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
      setMessages((m) => [...m, { role: "assistant", text: res.answer }]);
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

  return (
    <div>
      <PageHeader
        title="AI Financial Assistant"
        subtitle="Numbers come from you or the backend — never guessed by the AI"
      />
      <Panel className="mx-auto max-w-3xl">
        <div className="mb-4 flex items-center gap-2 text-white">
          <Bot className="h-5 w-5" />
          <h2 className="text-2xl font-semibold tracking-tight text-white">Conversation</h2>
        </div>

        <div className="mb-4 flex flex-wrap gap-2">
          {SUGGESTIONS.map((s) => (
            <button
              key={s}
              type="button"
              onClick={() => ask(s)}
              className="rounded-full border border-line bg-sand px-3 py-1.5 text-left text-xs font-medium text-ink hover:border-moss/40 hover:bg-moss/10"
            >
              {s}
            </button>
          ))}
        </div>

        <div className="max-h-[420px] space-y-3 overflow-y-auto rounded-2xl bg-[#0d1210] p-4">
          {messages.map((m, i) => (
            <div
              key={i}
              className={`max-w-[90%] whitespace-pre-wrap rounded-2xl px-4 py-3 text-sm leading-relaxed ${
                m.role === "user"
                  ? "ml-auto bg-moss text-black"
                  : "border border-line bg-card text-ink"
              }`}
            >
              {m.text}
            </div>
          ))}
          {loading ? <p className="text-sm text-muted">Analyzing your finances…</p> : null}
        </div>

        <form onSubmit={onSubmit} className="mt-4 flex gap-2">
          <Input
            placeholder="Ask a financial question…"
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
