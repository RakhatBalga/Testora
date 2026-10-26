import { Gauge } from "lucide-react";
import { Skeleton } from "@/shared/ui";

export type SkillBands = {
  reading: number | null;
  listening: number | null;
  writing: number | null;
  speaking: number | null;
};

export function BandSnapshot({
  loading,
  avgBand,
  skillBands,
  targetBand,
}: {
  loading: boolean;
  avgBand: number | null;
  skillBands: SkillBands;
  targetBand: number;
}) {
  return (
      <section className="animate-fade-up rounded-2xl border border-[var(--border)] bg-white p-6 shadow-sm shadow-slate-200/40 [animation-delay:20ms]">
        <div className="mb-5 flex items-center gap-2">
          <Gauge className="h-5 w-5 text-[var(--brand)]" />
          <h2 className="text-base font-semibold text-[var(--text-primary)]">Band snapshot</h2>
        </div>

        {loading ? (
          <div className="flex flex-col gap-6 sm:flex-row sm:items-center">
            <Skeleton className="mx-auto h-36 w-36 shrink-0 rounded-full sm:mx-0" />
            <div className="flex-1 space-y-4">
              {[0, 1, 2, 3].map((i) => (
                <Skeleton key={i} className="h-6 w-full rounded-lg" />
              ))}
            </div>
          </div>
        ) : (
          <>
            <div className="flex flex-col gap-6 sm:flex-row sm:items-center">
              <div className="relative mx-auto h-36 w-36 shrink-0 sm:mx-0">
                <BandRing value={avgBand} />
                <div className="absolute inset-0 flex flex-col items-center justify-center">
                  <span className="text-3xl font-extrabold tracking-tight text-[var(--text-primary)]">
                    {avgBand === null ? "-" : avgBand.toFixed(1)}
                  </span>
                  <span className="text-xs font-medium text-[var(--text-secondary)]">of 9.0</span>
                </div>
              </div>
              <div className="w-full flex-1 space-y-3">
                <SkillBandBar label="Reading" band={skillBands.reading} />
                <SkillBandBar label="Listening" band={skillBands.listening} />
                <SkillBandBar label="Writing" band={skillBands.writing} />
                <SkillBandBar label="Speaking" band={skillBands.speaking} />
              </div>
            </div>
            <p className="mt-5 text-sm text-[var(--text-secondary)]">
              {avgBand === null
                ? "Complete a graded test to see your average band."
                : avgBand >= targetBand
                  ? `You're at or above your target of ${targetBand.toFixed(1)}. Keep it steady.`
                  : `${(targetBand - avgBand).toFixed(1)} band to reach your target of ${targetBand.toFixed(1)}.`}
            </p>
          </>
        )}
      </section>
  );
}

function BandRing({ value }: { value: number | null }) {
  const max = 9;
  const pct = value === null ? 0 : Math.min(Math.max(value / max, 0), 1);
  const radius = 52;
  const circumference = 2 * Math.PI * radius;
  const dash = circumference * pct;
  return (
    <svg viewBox="0 0 120 120" className="h-36 w-36 -rotate-90">
      <circle cx="60" cy="60" r={radius} fill="none" stroke="var(--border)" strokeWidth="10" />
      <circle
        cx="60"
        cy="60"
        r={radius}
        fill="none"
        stroke="var(--brand)"
        strokeWidth="10"
        strokeLinecap="round"
        strokeDasharray={`${dash} ${circumference}`}
        className="transition-[stroke-dasharray] duration-700 ease-out"
      />
    </svg>
  );
}

function SkillBandBar({ label, band }: { label: string; band: number | null }) {
  const pct = band === null ? 0 : Math.min(Math.max(band / 9, 0), 1) * 100;
  return (
    <div>
      <div className="mb-1 flex items-center justify-between text-sm">
        <span className="font-medium text-[var(--text-primary)]">{label}</span>
        <span className="font-semibold text-[var(--text-secondary)]">
          {band === null ? "-" : band.toFixed(1)}
        </span>
      </div>
      <div className="h-2 overflow-hidden rounded-full bg-slate-100">
        <div
          className="h-full rounded-full bg-[var(--brand)] transition-[width] duration-700 ease-out"
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}
