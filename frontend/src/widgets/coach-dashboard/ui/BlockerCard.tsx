import Link from "next/link";
import { ArrowRight } from "lucide-react";
import { type Blocker } from "@/shared/api";

/** A concrete score blocker: criterion, explanation, capped band, fix CTA. */
export function BlockerCard({ blocker }: { blocker: Blocker }) {
  const { skill, criterion, explanation, band_cap, fix_href } = blocker;

  return (
    <div className="flex flex-col gap-4 rounded-2xl border border-[var(--border)] bg-white p-5 shadow-sm shadow-slate-200/40 sm:flex-row sm:items-center sm:justify-between">
      <div className="min-w-0">
        <div className="flex flex-wrap items-center gap-2">
          <span className="rounded-md bg-slate-100 px-2 py-0.5 text-xs font-semibold text-[var(--text-secondary)]">
            {skill}
          </span>
          <h3 className="font-semibold text-[var(--text-primary)]">{criterion}</h3>
        </div>
        <p className="mt-1.5 text-sm text-[var(--text-secondary)]">{explanation}</p>
        <p className="mt-2 text-xs font-semibold text-amber-600">
          Currently capping you at Band {band_cap.toFixed(1)}
        </p>
      </div>
      <Link
        href={fix_href}
        className="inline-flex h-10 flex-shrink-0 items-center justify-center gap-1.5 rounded-xl bg-[var(--brand)] px-4 text-sm font-semibold text-white shadow-sm shadow-[var(--brand)]/30 transition-all duration-200 hover:-translate-y-0.5 hover:bg-[var(--brand-dark)]"
      >
        Fix this
        <ArrowRight className="h-4 w-4" />
      </Link>
    </div>
  );
}
