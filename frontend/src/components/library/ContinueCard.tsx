import Link from "next/link";
import { ArrowRight, History } from "lucide-react";
import type { Test } from "@/lib/api";
import { accentFor, relativeTime, type TestProgress } from "./library";

type Props = {
  test: Test;
  href: string;
  progress: TestProgress;
};

/** High-visibility "resume where you left off" banner. Only shown when an
 *  unfinished local attempt exists. */
export function ContinueCard({ test, href, progress }: Props) {
  const accent = accentFor(test.test_type);

  return (
    <Link
      href={href}
      className={`group flex flex-col gap-4 rounded-2xl bg-white p-5 shadow-md shadow-slate-200/60 ring-1 ${accent.ring} transition-all duration-200 hover:-translate-y-0.5 hover:shadow-lg sm:flex-row sm:items-center sm:justify-between`}
    >
      <div className="min-w-0 flex-1">
        <p className={`flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide ${accent.text}`}>
          <History className="h-3.5 w-3.5" />
          Continue last session
        </p>
        <h3 className="mt-1.5 truncate text-lg font-bold text-slate-900">{test.title}</h3>
        <p className="mt-0.5 text-sm text-slate-500">
          {progress.answered} of {test.question_count ?? 0} questions answered
          {progress.updatedAt ? ` · ${relativeTime(progress.updatedAt)}` : ""}
        </p>
      </div>
      <span className="inline-flex flex-shrink-0 items-center gap-2 self-start rounded-xl bg-[var(--brand)] px-5 py-2.5 text-sm font-semibold text-white shadow-sm transition group-hover:bg-[var(--brand-dark)] sm:self-auto">
        Resume
        <ArrowRight className="h-4 w-4 transition-transform duration-200 group-hover:translate-x-0.5" />
      </span>
    </Link>
  );
}
