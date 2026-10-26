import { Target } from "lucide-react";
import { IELTS_BAND_OPTIONS } from "@/shared/config";

export function TargetBandPicker({
  loading,
  targetBand,
  savingTarget,
  onChange,
}: {
  loading: boolean;
  targetBand: number;
  savingTarget: boolean;
  onChange: (band: number) => void;
}) {
  return (
      <section className="animate-fade-up rounded-2xl border border-[var(--border)] bg-white p-6 shadow-sm shadow-slate-200/40 [animation-delay:60ms]">
        <div className="flex flex-col gap-5 lg:flex-row lg:items-center lg:justify-between">
          <div className="flex items-start gap-3">
            <span className="mt-0.5 flex shrink-0 items-center justify-center text-[var(--brand)]">
              <Target className="h-6 w-6" />
            </span>
            <div>
              <p className="text-xs font-semibold uppercase tracking-wide text-[var(--text-secondary)]">
                Target band
              </p>
              <p className="mt-1 text-2xl font-extrabold tracking-tight text-[var(--text-primary)]">
                {loading ? "..." : targetBand.toFixed(1)}
              </p>
            </div>
          </div>

          <div className="grid grid-cols-5 gap-2 sm:flex sm:flex-wrap sm:justify-end">
            {IELTS_BAND_OPTIONS.map((band) => {
              const active = band === targetBand;
              return (
                <button
                  key={band}
                  type="button"
                  aria-pressed={active}
                  disabled={loading || savingTarget}
                  onClick={() => onChange(band)}
                  className={`h-10 min-w-0 rounded-lg border px-2 text-sm font-semibold transition sm:min-w-14 sm:px-3 ${
                    active
                      ? "border-slate-950 bg-slate-950 text-white"
                      : "border-slate-200 bg-white text-slate-600 hover:border-slate-300 hover:text-slate-950"
                  } disabled:cursor-not-allowed disabled:opacity-60`}
                >
                  {band.toFixed(1)}
                </button>
              );
            })}
          </div>
        </div>
        {savingTarget && (
          <p className="mt-3 text-sm text-[var(--text-secondary)]">Saving target...</p>
        )}
      </section>
  );
}
