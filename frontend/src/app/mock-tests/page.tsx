"use client";

import { Clock, Target, Play, CheckCircle2, RotateCcw } from "lucide-react";
import { useRequireAuth } from "@/hooks/useRequireAuth";
import { mockTests, skillMeta, toneClasses, type MockTest } from "@/lib/dashboard";
import { PageHeader, skillIcons } from "@/components/dashboard/widgets";

const statusMeta: Record<MockTest["status"], { label: string; cta: string; icon: typeof Play }> = {
  new: { label: "Not started", cta: "Start Test", icon: Play },
  "in-progress": { label: "In progress", cta: "Resume Test", icon: RotateCcw },
  completed: { label: "Completed", cta: "Review", icon: CheckCircle2 },
};

export default function MockTestsPage() {
  const { token, ready } = useRequireAuth();
  if (!ready || !token) return null;

  return (
    <div className="space-y-8">
      <PageHeader
        title="Mock Tests"
        subtitle="Full IELTS Academic simulations under real exam conditions — all four sections, timed."
      />

      <div className="grid gap-5">
        {mockTests.map((test, i) => {
          const sm = statusMeta[test.status];
          const StatusIcon = sm.icon;
          const hours = Math.floor(test.durationMin / 60);
          const mins = test.durationMin % 60;
          return (
            <div
              key={test.id}
              className="animate-fade-up overflow-hidden rounded-3xl border border-[var(--border)] bg-white shadow-sm shadow-slate-200/40"
              style={{ animationDelay: `${i * 80}ms` }}
            >
              <div className="flex flex-col gap-6 p-6 sm:flex-row sm:items-center sm:justify-between sm:p-7">
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-3">
                    <h2 className="text-xl font-bold text-[var(--text-primary)]">{test.title}</h2>
                    <span
                      className={`rounded-full px-2.5 py-0.5 text-xs font-semibold ${
                        test.status === "completed"
                          ? "bg-emerald-50 text-emerald-600"
                          : test.status === "in-progress"
                            ? "bg-amber-50 text-amber-600"
                            : "bg-slate-100 text-[var(--text-secondary)]"
                      }`}
                    >
                      {sm.label}
                    </span>
                  </div>

                  {/* sections */}
                  <div className="mt-4 flex flex-wrap gap-2">
                    {test.sections.map((s) => {
                      const m = skillMeta[s];
                      const t = toneClasses[m.tone];
                      const Icon = skillIcons[s];
                      return (
                        <span
                          key={s}
                          className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1.5 text-xs font-medium ${t.soft}`}
                        >
                          <Icon className="h-3.5 w-3.5" />
                          {m.label}
                        </span>
                      );
                    })}
                  </div>

                  <div className="mt-5 flex flex-wrap gap-6 text-sm">
                    <span className="inline-flex items-center gap-1.5 text-[var(--text-secondary)]">
                      <Clock className="h-4 w-4" />
                      {hours}h {mins}m
                    </span>
                    <span className="inline-flex items-center gap-1.5 text-[var(--text-secondary)]">
                      <Target className="h-4 w-4" />
                      Expected band{" "}
                      <strong className="font-bold text-[var(--text-primary)]">
                        {test.expectedBand.toFixed(1)}
                      </strong>
                    </span>
                  </div>
                </div>

                <button
                  type="button"
                  className={`inline-flex h-12 flex-shrink-0 items-center justify-center gap-2 rounded-xl px-6 text-sm font-semibold transition-all duration-200 ${
                    test.status === "completed"
                      ? "border border-[var(--border)] text-[var(--text-primary)] hover:bg-slate-50"
                      : "bg-[var(--brand)] text-white shadow-sm shadow-[var(--brand)]/30 hover:-translate-y-0.5 hover:bg-[var(--brand-dark)]"
                  }`}
                >
                  <StatusIcon className="h-4 w-4" />
                  {sm.cta}
                </button>
              </div>
            </div>
          );
        })}
      </div>

      <p className="text-center text-sm text-[var(--text-secondary)]">
        More full tests are added every week. Your band estimate updates after each completed simulation.
      </p>
    </div>
  );
}
