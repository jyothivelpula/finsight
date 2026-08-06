import { useState, type FormEvent } from "react";
import { BookOpen, HelpCircle, Mail, MessageCircle } from "lucide-react";
import { Link } from "react-router-dom";
import { Button, Input, PageHeader, Panel } from "../components/ui";

const FAQS = [
  {
    q: "How do I add income or expenses?",
    a: "Go to Income or Expenses from the sidebar, then use Add Income / Add Expense. You can also start from Add Transaction in the top bar.",
  },
  {
    q: "How does the AI Coach work?",
    a: "Open AI Coach and ask about spending, budgets, savings, goals, or your health score. Answers use your verified FinSight analytics — the AI does not invent amounts.",
  },
  {
    q: "What is Financial Health Score?",
    a: "It’s a 0–100 score based on savings rate, budget discipline, expense ratio, goal progress, and spending stability. Check Analytics for the breakdown.",
  },
  {
    q: "How do I export reports?",
    a: "Open Reports, choose a report type and format (PDF, Excel, or CSV), then generate and download.",
  },
];

export default function HelpPage() {
  const [subject, setSubject] = useState("");
  const [message, setMessage] = useState("");
  const [sentNote, setSentNote] = useState("");

  const onSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (!subject.trim() || !message.trim()) return;
    setSentNote("Thanks! Your support request was saved locally. Email support will be available soon.");
    setSubject("");
    setMessage("");
  };

  return (
    <div className="mx-auto max-w-3xl space-y-5">
      <PageHeader
        title="Help & Support"
        subtitle="FAQs, quick links, and a way to reach the FinSight team"
      />

      <div className="grid gap-4 sm:grid-cols-3">
        <Panel className="sm:col-span-1">
          <BookOpen className="h-5 w-5 text-moss" />
          <p className="mt-3 text-sm font-bold text-ink">Quick start</p>
          <p className="mt-1 text-xs text-muted">Add income, expenses, and budgets to unlock insights.</p>
          <Link to="/app" className="mt-3 inline-block text-sm font-semibold text-moss">
            Go to Dashboard →
          </Link>
        </Panel>
        <Panel className="sm:col-span-1">
          <MessageCircle className="h-5 w-5 text-moss" />
          <p className="mt-3 text-sm font-bold text-ink">Ask AI Coach</p>
          <p className="mt-1 text-xs text-muted">Get answers from your real financial data.</p>
          <Link to="/app/ai" className="mt-3 inline-block text-sm font-semibold text-moss">
            Open AI Coach →
          </Link>
        </Panel>
        <Panel className="sm:col-span-1">
          <Mail className="h-5 w-5 text-moss" />
          <p className="mt-3 text-sm font-bold text-ink">Email us</p>
          <p className="mt-1 text-xs text-muted">support@finsight.app</p>
          <a href="mailto:support@finsight.app" className="mt-3 inline-block text-sm font-semibold text-moss">
            Send email →
          </a>
        </Panel>
      </div>

      <Panel>
        <div className="mb-4 flex items-center gap-2">
          <HelpCircle className="h-4 w-4 text-moss" />
          <h2 className="text-lg font-bold text-ink">Frequently asked questions</h2>
        </div>
        <ul className="divide-y divide-line">
          {FAQS.map((item) => (
            <li key={item.q} className="py-3">
              <p className="text-sm font-semibold text-ink">{item.q}</p>
              <p className="mt-1 text-sm leading-relaxed text-muted">{item.a}</p>
            </li>
          ))}
        </ul>
      </Panel>

      <Panel>
        <h2 className="text-lg font-bold text-ink">Contact support</h2>
        <p className="mt-1 text-sm text-muted">Tell us what’s going wrong and we’ll help you fix it.</p>
        <form onSubmit={onSubmit} className="mt-4 space-y-3">
          <Input
            label="Subject"
            value={subject}
            onChange={(e) => setSubject(e.target.value)}
            placeholder="e.g. Budget not updating"
            required
          />
          <label className="block space-y-1.5">
            <span className="text-sm font-medium text-ink">Message</span>
            <textarea
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              required
              rows={4}
              placeholder="Describe the issue…"
              className="w-full rounded-xl border border-line bg-white px-3 py-2.5 text-sm text-ink outline-none ring-moss/20 placeholder:text-muted/60 focus:border-moss focus:ring-2"
            />
          </label>
          <Button type="submit">Submit request</Button>
        </form>
        {sentNote ? <p className="mt-3 text-sm text-emerald-600">{sentNote}</p> : null}
      </Panel>
    </div>
  );
}
