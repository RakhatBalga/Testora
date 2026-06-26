import Link from "next/link";
import { ArrowRight, CheckCircle2, Clock, FileText } from "lucide-react";
import type { Test } from "@/shared/api";
import { accentFor, type TestProgress } from "../model/library";

type Props = {
  test: Test;
  href: string;
  progress: TestProgress;
};

export function TestCard({ test, href, progress }: Props) {
  const accent = accentFor(test.test_type);
  const { status, band } = progress;

  const cta =
    status === "completed" ? "Review" : status === "in_progress" ? "Continue" : "Start test";

  return (
    <Link
      href={href}
      className="group flex flex-col rounded-2xl bg-white p-5 shadow-sm shadow-slate-200/50 ring-1 ring-slate-100 transition-all duration-200 hover:-translate-y-1 hover:shadow-lg hover:shadow-slate-200/70"
    >
      <h3 className="font-semibold leading-snug text-slate-900 group-hover:text-slate-950">
        {test.title}
      </h3>

      <div className="mt-3 flex flex-wrap gap-2">
        <span className={`rounded-lg px-2.5 py-1 text-xs font-semibold capitalize ${accent.softBg} ${accent.text}`}>
          {test.test_type}
        </span>
        {test.difficulty && (
          <span className="rounded-lg bg-slate-100 px-2.5 py-1 text-xs font-semibold text-slate-500">
            {test.difficulty}
          </span>
        )}
      </div>

      <div className="mt-3 flex items-center gap-4 text-sm text-slate-500">
        <span className="inline-flex items-center gap-1.5">
          <FileText className="h-4 w-4 text-slate-300" />
          {test.question_count ?? 0} questions
        </span>
        <span className="inline-flex items-center gap-1.5">
          <Clock className="h-4 w-4 text-slate-300" />
          {test.duration_minutes} min
        </span>
      </div>

      {status === "completed" && (
        <span className="mt-4 inline-flex items-center gap-1.5 text-sm font-medium text-emerald-600">
          <CheckCircle2 className="h-4 w-4" />
          Completed{band !== null ? ` · Band ${band.toFixed(1)}` : ""}
        </span>
      )}

      <div className="mt-5 flex items-center justify-between border-t border-slate-100 pt-4">
        <span className={`text-sm font-semibold ${accent.text}`}>{cta}</span>
        <ArrowRight className={`h-4 w-4 ${accent.text} transition-transform duration-200 group-hover:translate-x-1`} />
      </div>
    </Link>
  );
}
