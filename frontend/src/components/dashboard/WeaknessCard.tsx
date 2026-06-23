import { Repeat } from "lucide-react";
import { type Weakness } from "@/lib/api";
import { ProgressBar } from "@/components/dashboard/widgets";

const SEVERITY_LABEL = ["", "minor", "moderate", "high"];

/** A single aggregated weakness: name, frequency, severity, recurring badge, score. */
export function WeaknessCard({ weakness }: { weakness: Weakness }) {
  const { label, skill, frequency, avg_severity, recurring, score } = weakness;
  const sev = Math.round(avg_severity);

  return (
    <div className="rounded-2xl border border-[var(--border)] bg-white p-4 shadow-sm shadow-slate-200/40">
      <div className="flex items-start justify-between gap-2">
        <p className="font-semibold text-[var(--text-primary)]">{label}</p>
        {recurring && (
          <span className="inline-flex flex-shrink-0 items-center gap-1 rounded-full bg-amber-50 px-2 py-0.5 text-[11px] font-semibold text-amber-600">
            <Repeat className="h-3 w-3" />
            Recurring
          </span>
        )}
      </div>

      <div className="mt-1 flex flex-wrap items-center gap-x-2 gap-y-0.5 text-xs text-[var(--text-secondary)]">
        <span className="capitalize">{skill}</span>
        <span>·</span>
        <span>{frequency} attempt{frequency === 1 ? "" : "s"}</span>
        <span>·</span>
        <span>{SEVERITY_LABEL[sev] ?? "moderate"} severity</span>
      </div>

      <div className="mt-3 flex items-center gap-2">
        <ProgressBar value={score} className="flex-1" barClass="bg-amber-500" />
        <span className="w-9 text-right text-sm font-bold text-[var(--text-primary)]">
          {score.toFixed(2)}
        </span>
      </div>
    </div>
  );
}
