"use client";

import { type BreakdownItem } from "@/shared/api";

/** Performance-by-question-type bars on the result screen. */
export function ResultBreakdown({ breakdown }: { breakdown: BreakdownItem[] }) {
  if (!breakdown || breakdown.length === 0) return null;

  return (
    <div className="rounded-3xl border border-[var(--border)] bg-white p-6 shadow-sm sm:p-7">
      <h2 className="text-base font-semibold text-[var(--text-primary)]">Performance by question type</h2>
      <p className="mt-1 text-xs text-[var(--text-secondary)]">Weakest type first — where to focus next.</p>

      <div className="mt-5 space-y-4">
        {breakdown.map((b) => {
          const tone =
            b.accuracy >= 70 ? "bg-emerald-500" : b.accuracy >= 40 ? "bg-amber-500" : "bg-red-500";
          return (
            <div key={b.question_type}>
              <div className="mb-1.5 flex items-center justify-between text-sm">
                <span className="font-medium text-[var(--text-primary)]">{b.label}</span>
                <span className="font-semibold text-[var(--text-secondary)]">
                  {b.correct}/{b.total} · {b.accuracy}%
                </span>
              </div>
              <div className="h-2.5 w-full overflow-hidden rounded-full bg-slate-100">
                <div className={`h-full rounded-full ${tone} transition-all`} style={{ width: `${b.accuracy}%` }} />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
