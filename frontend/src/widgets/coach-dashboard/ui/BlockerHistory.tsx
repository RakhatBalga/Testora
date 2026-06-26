"use client";

import { History, Sparkles } from "lucide-react";
import { type BlockerHistory as BlockerHistoryData } from "@/shared/api";

/**
 * Week-by-week timeline of the user's main blocker, so a long-standing
 * limitation being dethroned is visible at a glance. Fed by
 * /analytics/blocker-history (pure aggregation).
 */
export function BlockerHistory({ data, loading }: { data: BlockerHistoryData | null; loading: boolean }) {
  return (
    <section className="rounded-3xl border border-[var(--border)] bg-white p-6 shadow-sm shadow-slate-200/40 sm:p-7">
      <div className="mb-4 flex items-center gap-2">
        <History className="h-5 w-5 text-[var(--brand)]" />
        <h2 className="text-base font-semibold text-[var(--text-primary)]">Blocker history</h2>
      </div>

      {loading ? (
        <div className="flex gap-3">
          {[0, 1, 2, 3].map((i) => (
            <div key={i} className="h-16 flex-1 animate-pulse rounded-2xl bg-slate-50" />
          ))}
        </div>
      ) : data && data.has_data && data.history.length > 0 ? (
        <>
          <ol className="flex flex-wrap gap-2.5">
            {data.history.map((p, i) => (
              <li
                key={`${p.label}-${i}`}
                className={`flex min-w-[120px] flex-1 flex-col gap-1 rounded-2xl border p-3 ${
                  p.changed
                    ? "border-[var(--brand)]/40 bg-[var(--brand)]/[0.06]"
                    : "border-[var(--border)] bg-white"
                }`}
              >
                <span className="text-[0.7rem] font-medium uppercase tracking-wide text-[var(--text-secondary)]">
                  {p.label}
                </span>
                <span className="flex items-center gap-1.5 text-sm font-semibold text-[var(--text-primary)]">
                  {p.changed && <Sparkles className="h-3.5 w-3.5 flex-shrink-0 text-[var(--brand)]" />}
                  {p.blocker}
                </span>
              </li>
            ))}
          </ol>

          {data.note && (
            <p className="mt-4 rounded-xl bg-emerald-50 px-4 py-3 text-sm font-medium text-emerald-700">
              {data.note}
            </p>
          )}
        </>
      ) : (
        <div className="flex items-center gap-3 rounded-2xl border border-dashed border-[var(--border)] p-6 text-sm text-[var(--text-secondary)]">
          <History className="h-5 w-5 text-slate-400" />
          Practice across a couple of weeks and I&apos;ll track how your main blocker shifts.
        </div>
      )}
    </section>
  );
}
