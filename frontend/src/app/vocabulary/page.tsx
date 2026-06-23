"use client";

import { BookMarked, Loader, AlertTriangle, CalendarClock, ArrowRight } from "lucide-react";
import { useRequireAuth } from "@/hooks/useRequireAuth";
import { vocabulary } from "@/lib/dashboard";
import { PageHeader } from "@/components/dashboard/widgets";

const statusStyle: Record<string, { label: string; cls: string }> = {
  known: { label: "Known", cls: "bg-emerald-50 text-emerald-600" },
  learning: { label: "Learning", cls: "bg-sky-50 text-sky-600" },
  weak: { label: "Weak", cls: "bg-amber-50 text-amber-600" },
};

export default function VocabularyPage() {
  const { token, ready } = useRequireAuth();
  if (!ready || !token) return null;

  const cards = [
    { label: "Learned Words", value: vocabulary.learned, icon: BookMarked, accent: "text-emerald-500", soft: "bg-emerald-50" },
    { label: "Words In Progress", value: vocabulary.inProgress, icon: Loader, accent: "text-sky-500", soft: "bg-sky-50" },
    { label: "Weak Words", value: vocabulary.weak, icon: AlertTriangle, accent: "text-amber-500", soft: "bg-amber-50" },
    { label: "Daily Review", value: vocabulary.dailyReviewDue, icon: CalendarClock, accent: "text-[var(--brand)]", soft: "bg-[var(--brand)]/[0.08]" },
  ];

  return (
    <div className="space-y-8">
      <PageHeader
        title="Vocabulary"
        subtitle="Build the academic word bank that lifts your Reading, Writing and Speaking bands."
        action={
          <button
            type="button"
            className="inline-flex h-11 items-center gap-2 rounded-xl bg-[var(--brand)] px-5 text-sm font-semibold text-white shadow-sm shadow-[var(--brand)]/30 transition-all duration-200 hover:-translate-y-0.5 hover:bg-[var(--brand-dark)]"
          >
            Start daily review
            <ArrowRight className="h-4 w-4" />
          </button>
        }
      />

      {/* summary cards */}
      <div className="grid animate-fade-up gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {cards.map((c) => (
          <div
            key={c.label}
            className="rounded-2xl border border-[var(--border)] bg-white p-5 shadow-sm shadow-slate-200/40"
          >
            <span className={`flex h-10 w-10 items-center justify-center rounded-xl ${c.soft} ${c.accent}`}>
              <c.icon className="h-5 w-5" />
            </span>
            <p className="mt-3 text-3xl font-extrabold tracking-tight text-[var(--text-primary)]">
              {c.value}
            </p>
            <p className="text-sm text-[var(--text-secondary)]">{c.label}</p>
          </div>
        ))}
      </div>

      {/* word list */}
      <section className="animate-fade-up overflow-hidden rounded-3xl border border-[var(--border)] bg-white shadow-sm shadow-slate-200/40 [animation-delay:80ms]">
        <div className="border-b border-[var(--border)] px-6 py-4">
          <h2 className="text-base font-semibold text-[var(--text-primary)]">Your words</h2>
        </div>
        <div className="divide-y divide-[var(--border)]">
          {vocabulary.words.map((w) => {
            const s = statusStyle[w.status];
            return (
              <div key={w.word} className="flex items-center gap-4 px-6 py-4">
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <p className="font-semibold text-[var(--text-primary)]">{w.word}</p>
                    <span className={`rounded-full px-2 py-0.5 text-[11px] font-semibold ${s.cls}`}>
                      {s.label}
                    </span>
                  </div>
                  <p className="mt-0.5 text-sm text-[var(--text-secondary)]">{w.meaning}</p>
                </div>
                <span className="hidden rounded-full bg-slate-100 px-2.5 py-1 text-xs font-medium text-[var(--text-secondary)] sm:inline">
                  {w.topic}
                </span>
              </div>
            );
          })}
        </div>
      </section>
    </div>
  );
}
