import { CalendarDays } from "lucide-react";
import { Skeleton } from "@/shared/ui";
import type { ActivitySummary } from "@/entities/profile";

export function ActivityHeatmap({ loading, activity }: { loading: boolean; activity: ActivitySummary }) {
  return (
      <section className="animate-fade-up rounded-2xl border border-[var(--border)] bg-white p-6 shadow-sm shadow-slate-200/40 [animation-delay:40ms]">
        <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <CalendarDays className="h-5 w-5 text-[var(--brand)]" />
            <h2 className="text-base font-semibold text-[var(--text-primary)]">Activity</h2>
          </div>
          {!loading && (
            <p className="text-sm text-[var(--text-secondary)]">
              Active days: <span className="font-semibold text-[var(--text-primary)]">{activity.activeDays}</span>
              <span className="px-2 text-slate-300">·</span>
              Current streak: <span className="font-semibold text-[var(--text-primary)]">{activity.currentStreak}</span>
              <span className="px-2 text-slate-300">·</span>
              Best streak: <span className="font-semibold text-[var(--text-primary)]">{activity.maxStreak}</span>
            </p>
          )}
        </div>

        {loading ? (
          <Skeleton className="h-28 w-full rounded-xl" />
        ) : (
          <>
            <p className="mb-4 text-sm text-[var(--text-secondary)]">
              <span className="font-semibold text-[var(--text-primary)]">{activity.total}</span> session
              {activity.total === 1 ? "" : "s"} in the past year
            </p>
            <div className="overflow-x-auto pb-1">
              <div className="flex w-full min-w-[560px] gap-[3px]">
                {activity.weeks.map((week, wi) => (
                  <div key={wi} className="flex flex-1 flex-col gap-[3px]">
                    {week.map((cell, di) => (
                      <span
                        key={cell.key || `${wi}-${di}`}
                        title={cell.future ? undefined : `${cell.count} session${cell.count === 1 ? "" : "s"} · ${cell.key}`}
                        className={`aspect-square w-full rounded-[2px] ${heatClass(cell.count, cell.future)}`}
                      />
                    ))}
                  </div>
                ))}
              </div>
            </div>
            <div className="mt-3 flex items-center justify-end gap-1.5 text-xs text-[var(--text-secondary)]">
              <span>Less</span>
              <span className="h-3 w-3 rounded-[3px] bg-slate-100" />
              <span className="h-3 w-3 rounded-[3px] bg-[var(--brand)]/30" />
              <span className="h-3 w-3 rounded-[3px] bg-[var(--brand)]/55" />
              <span className="h-3 w-3 rounded-[3px] bg-[var(--brand)]/80" />
              <span className="h-3 w-3 rounded-[3px] bg-[var(--brand)]" />
              <span>More</span>
            </div>
          </>
        )}
      </section>
  );
}

function heatClass(count: number, future: boolean): string {
  if (future) return "bg-transparent";
  if (count <= 0) return "bg-slate-100";
  if (count === 1) return "bg-[var(--brand)]/30";
  if (count === 2) return "bg-[var(--brand)]/55";
  if (count === 3) return "bg-[var(--brand)]/80";
  return "bg-[var(--brand)]";
}
