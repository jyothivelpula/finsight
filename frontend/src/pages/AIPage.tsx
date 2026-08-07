import type { FormEvent } from "react";
import { Bot, Eraser, Send } from "lucide-react";
import { Button, Input, PageHeader, Panel } from "../components/ui";
import { useAiChat } from "../hooks/useAiChat";
import { currentYearMonth } from "../lib/format";

export default function AIPage() {
  const { year, month } = currentYearMonth();
  const {
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
  } = useAiChat({ year, month });

  const onSubmit = (e: FormEvent) => {
    e.preventDefault();
    ask(input);
  };

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

        <div
          ref={chatContainerRef}
          className="max-h-[480px] space-y-3 overflow-y-auto rounded-2xl border border-line bg-sand/50 p-4"
        >
          {messages.map((m, i) => (
            <div key={m.id} className={m.role === "user" ? "flex justify-end" : "space-y-2"}>
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
                      disabled={loading}
                      onClick={() => ask(action)}
                      className="rounded-full border border-moss/20 bg-white px-3 py-1.5 text-xs font-medium text-moss hover:bg-soft disabled:opacity-50"
                    >
                      {action}
                    </button>
                  ))}
                </div>
              ) : null}
            </div>
          ))}
          {loading ? <p className="text-sm text-muted">Thinking…</p> : null}
          <div ref={chatEndRef} aria-hidden className="h-px w-full shrink-0" />
        </div>

        <form onSubmit={onSubmit} className="mt-4 flex gap-2">
          <Input
            placeholder='Try “I spent ₹500 on food” or ask about your budget…'
            value={input}
            onChange={(e) => setInput(e.target.value)}
            className="flex-1"
          />
          <Button type="submit" disabled={loading || !input.trim()}>
            <Send className="h-4 w-4" /> Ask
          </Button>
        </form>
      </Panel>
    </div>
  );
}
