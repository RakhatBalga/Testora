import { Clock, Pause, Play } from "lucide-react";
import { formatClock } from "../model/types";

type Props = {
  remaining: number | null;
  paused: boolean;
  onPause: () => void;
  onResume: () => void;
};

export function ReadingTimer({ remaining, paused, onPause, onResume }: Props) {
  if (remaining === null) return null;
  const low = remaining < 60 && !paused;

  return (
    <div className="flex items-center gap-2">
      <div
        className={`flex items-center gap-1.5 rounded-xl px-3 py-1.5 font-mono text-lg font-semibold tabular-nums transition-colors ${
          paused
            ? "bg-slate-100 text-slate-400"
            : low
              ? "animate-pulse bg-red-100 text-red-700"
              : "bg-slate-100 text-slate-700"
        }`}
      >
        <Clock className="h-4 w-4" />
        {formatClock(remaining)}
      </div>
      <button
        type="button"
        onClick={paused ? onResume : onPause}
        aria-label={paused ? "Resume timer" : "Pause timer"}
        className="flex h-9 w-9 items-center justify-center rounded-xl border border-[var(--border)] text-slate-600 transition hover:bg-slate-50"
      >
        {paused ? <Play className="h-4 w-4" /> : <Pause className="h-4 w-4" />}
      </button>
    </div>
  );
}
