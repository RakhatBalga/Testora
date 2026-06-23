"use client";

import Link from "next/link";
import { ArrowUpRight, Lightbulb } from "lucide-react";
import type { Recommendation } from "@/lib/api";

const IMPACT_CLASSES: Record<string, string> = {
  High: "bg-red-50 text-red-600",
  Medium: "bg-amber-50 text-amber-600",
  Low: "bg-slate-100 text-slate-500",
};

const PRIORITY_CLASSES: Record<number, string> = {
  1: "bg-[var(--brand)] text-white",
  2: "bg-[var(--brand)]/20 text-[var(--brand)]",
  3: "bg-slate-100 text-slate-500",
  4: "bg-slate-100 text-slate-500",
  5: "bg-slate-100 text-slate-500",
};

function priorityLabel(p: number): string {
  if (p === 1) return "Top pick";
  if (p === 2) return `#${p}`;
  return `#${p}`;
}

interface Props {
  recommendations: Recommendation[] | null;
}

export function Recommendations({ recommendations }: Props) {
  return (
    <section className="animate-fade-up rounded-3xl border border-[var(--border)] bg-white p-6 shadow-sm shadow-slate-200/40 [animation-delay:260ms] sm:p-7">
      <div className="mb-5 flex items-center gap-2">
        <Lightbulb className="h-5 w-5 text-[var(--brand)]" />
        <h2 className="text-base font-semibold text-[var(--text-primary)]">Recommended next</h2>
      </div>

      {recommendations === null ? (
        <div className="space-y-3">
          {[...Array(3)].map((_, i) => (
            <div key={i} className="h-20 animate-pulse rounded-2xl bg-slate-50" />
          ))}
        </div>
      ) : recommendations.length === 0 ? (
        <div className="flex items-center gap-3 rounded-2xl border border-dashed border-[var(--border)] p-6 text-sm text-[var(--text-secondary)]">
          <Lightbulb className="h-5 w-5 text-slate-400" />
          Complete a practice task to get personalised recommendations.
        </div>
      ) : (
        <ol className="space-y-3">
          {recommendations.map((rec) => (
            <li key={rec.id}>
              <Link
                href={rec.href}
                className="group flex items-start gap-4 rounded-2xl border border-[var(--border)] p-4 transition-colors hover:border-slate-300 hover:bg-slate-50"
              >
                {/* Priority badge */}
                <span
                  className={`flex h-8 w-16 flex-shrink-0 items-center justify-center rounded-xl text-[10px] font-bold uppercase tracking-wide ${PRIORITY_CLASSES[rec.priority] ?? PRIORITY_CLASSES[5]}`}
                >
                  {priorityLabel(rec.priority)}
                </span>

                {/* Content */}
                <span className="min-w-0 flex-1">
                  <span className="flex items-center gap-2">
                    <span className="block text-sm font-semibold text-[var(--text-primary)]">
                      {rec.title}
                    </span>
                    <span
                      className={`rounded-full px-2 py-0.5 text-[10px] font-semibold ${IMPACT_CLASSES[rec.estimated_impact] ?? IMPACT_CLASSES.Low}`}
                    >
                      {rec.estimated_impact} impact
                    </span>
                  </span>
                  <span className="mt-0.5 block text-xs text-[var(--text-secondary)]">
                    {rec.reason}
                    {rec.estimated_minutes ? ` · ${rec.estimated_minutes} min` : ""}
                  </span>
                </span>

                <ArrowUpRight className="h-4 w-4 flex-shrink-0 text-slate-300 transition-colors group-hover:text-[var(--brand)]" />
              </Link>
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}
