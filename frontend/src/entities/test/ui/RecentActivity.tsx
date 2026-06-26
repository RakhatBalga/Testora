import Link from "next/link";
import type { AttemptSummary } from "@/shared/api";
import { relativeTime } from "../model/library";

function bandTone(band: number | null): string {
  if (band === null) return "bg-slate-100 text-slate-500";
  if (band >= 7) return "bg-emerald-50 text-emerald-700";
  if (band >= 5.5) return "bg-amber-50 text-amber-700";
  return "bg-rose-50 text-rose-700";
}

function resultHref(attempt: AttemptSummary): string {
  return attempt.test_type === "listening"
    ? `/listening/result/${attempt.id}`
    : `/result/${attempt.id}`;
}

/** Compact timeline of recent completed attempts for this skill. */
export function RecentActivity({ attempts }: { attempts: AttemptSummary[] }) {
  if (attempts.length === 0) return null;

  return (
    <section>
      <h2 className="mb-3 text-sm font-semibold text-slate-900">Recent activity</h2>
      <div className="overflow-hidden rounded-2xl bg-white shadow-sm shadow-slate-200/50 ring-1 ring-slate-100">
        {attempts.slice(0, 5).map((a, i) => (
          <Link
            key={a.id}
            href={resultHref(a)}
            className={`flex items-center justify-between px-5 py-3 transition hover:bg-slate-50 ${
              i > 0 ? "border-t border-slate-100" : ""
            }`}
          >
            <div className="min-w-0">
              <p className="truncate text-sm font-medium text-slate-800">{a.test_title}</p>
              <p className="text-xs text-slate-400">{relativeTime(a.created_at)}</p>
            </div>
            <span
              className={`flex-shrink-0 rounded-md px-2 py-0.5 text-xs font-semibold ${bandTone(a.band)}`}
            >
              {a.band !== null ? `Band ${a.band.toFixed(1)}` : `${a.score}/${a.total}`}
            </span>
          </Link>
        ))}
      </div>
    </section>
  );
}
