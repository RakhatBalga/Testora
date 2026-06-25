"use client";

import { type ReactNode, useEffect, useMemo, useState } from "react";
import { Activity, AlertTriangle, Flame, ListChecks, Target, TrendingUp } from "lucide-react";
import { useRequireAuth } from "@/hooks/useRequireAuth";
import {
  api,
  type BandGapResult,
  type BandTrajectoryResult,
  type Streak,
  type Weakness,
} from "@/lib/api";
import { SKILLS, skillMeta, toneClasses, type Skill } from "@/lib/dashboard";
import { BandTrajectory } from "@/components/dashboard/BandTrajectory";
import { PageHeader, ProgressBar, StatTile, skillIcons } from "@/components/dashboard/widgets";
import { Skeleton } from "@/components/ui/Skeleton";

const TARGET_BAND = 7.5;

export default function AnalyticsPage() {
  const { token, ready } = useRequireAuth();
  const [bandGap, setBandGap] = useState<BandGapResult | null>(null);
  const [trajectory, setTrajectory] = useState<BandTrajectoryResult | null>(null);
  const [weaknesses, setWeaknesses] = useState<Weakness[] | null>(null);
  const [streak, setStreak] = useState<Streak | null>(null);
  const [historyTotal, setHistoryTotal] = useState<number | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!token) return;
    let active = true;

    const settle = <T,>(promise: Promise<T>, apply: (value: T) => void, fallback: T) => {
      promise
        .then((value) => active && apply(value))
        .catch((err) => {
          if (!active) return;
          setError((prev) => prev || err.message || "Analytics failed to load.");
          apply(fallback);
        });
    };

    settle(
      api.getBandGap(TARGET_BAND),
      setBandGap,
      { current: null, target: TARGET_BAND, gap: null, per_skill: {}, lowest_skill: null, has_data: false }
    );
    settle(api.getBandTrajectory(), setTrajectory, { points: [], delta: null, has_data: false });
    settle(api.getWeaknesses(5), (w) => setWeaknesses(w.weaknesses), { weaknesses: [] });
    settle(api.getStreak(), setStreak, { current_streak: 0, active_today: false });
    settle(api.getHistory(undefined, "newest"), (h) => setHistoryTotal(h.total), { items: [], total: 0 });

    return () => {
      active = false;
    };
  }, [token]);

  const loading =
    bandGap === null || trajectory === null || weaknesses === null || streak === null || historyTotal === null;

  const target = bandGap?.target ?? TARGET_BAND;
  const perSkill = useMemo(() => bandGap?.per_skill ?? {}, [bandGap]);

  if (!ready || !token) return null;

  return (
    <div className="space-y-8">
      <PageHeader
        title="Analytics"
        subtitle="Track your band trajectory and see exactly where to focus next."
      />

      {error && <p className="rounded-xl bg-red-50 px-4 py-3 text-sm text-red-600">{error}</p>}

      <div className="grid animate-fade-up gap-4 sm:grid-cols-2 lg:grid-cols-5">
        <StatTile
          label="Current Band"
          value={bandGap?.current != null ? bandGap.current.toFixed(1) : "—"}
          hint={bandGap?.has_data ? "from graded attempts" : "no graded data yet"}
          icon={<TrendingUp className="h-5 w-5" />}
        />
        <StatTile
          label="Target Band"
          value={target.toFixed(1)}
          hint="default goal"
          icon={<Target className="h-5 w-5" />}
        />
        <StatTile
          label="Completed"
          value={loading ? "—" : String(historyTotal ?? 0)}
          hint="saved attempts"
          icon={<ListChecks className="h-5 w-5" />}
          accent="text-emerald-500"
        />
        <StatTile
          label="Streak"
          value={loading ? "—" : `${streak?.current_streak ?? 0}d`}
          hint={streak?.active_today ? "active today" : "practice today to extend it"}
          icon={<Flame className="h-5 w-5" />}
          accent="text-amber-500"
        />
        <StatTile
          label="Focus Areas"
          value={loading ? "—" : String(weaknesses?.length ?? 0)}
          hint="from recurring mistakes"
          icon={<Activity className="h-5 w-5" />}
          accent="text-sky-500"
        />
      </div>

      <section className="animate-fade-up rounded-3xl border border-[var(--border)] bg-white p-6 shadow-sm shadow-slate-200/40 [animation-delay:80ms] sm:p-7">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h2 className="text-base font-semibold text-[var(--text-primary)]">Band trajectory</h2>
          {trajectory?.has_data && trajectory.delta != null && (
            <span
              className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-semibold ${
                trajectory.delta >= 0 ? "bg-emerald-50 text-emerald-600" : "bg-red-50 text-red-600"
              }`}
            >
              <TrendingUp className="h-3.5 w-3.5" />
              {trajectory.delta >= 0 ? "+" : ""}
              {trajectory.delta.toFixed(1)} overall
            </span>
          )}
        </div>
        {trajectory === null ? (
          <Skeleton className="mt-5 h-60 w-full rounded-2xl" />
        ) : trajectory.points.length > 0 ? (
          <BandTrajectory points={trajectory.points} target={target} />
        ) : (
          <EmptyAnalyticsState
            icon={<TrendingUp className="h-5 w-5" />}
            text="Complete a graded Reading or Writing task and your trajectory will appear here."
          />
        )}
      </section>

      <section className="grid animate-fade-up gap-5 [animation-delay:120ms] sm:grid-cols-2">
        {SKILLS.map((skill) => (
          <SkillBandCard key={skill} skill={skill} band={perSkill[skill]} />
        ))}
      </section>

      <section className="animate-fade-up rounded-3xl border border-[var(--border)] bg-white p-6 shadow-sm shadow-slate-200/40 [animation-delay:160ms] sm:p-7">
        <div className="mb-4 flex items-center gap-2">
          <AlertTriangle className="h-5 w-5 text-amber-500" />
          <h2 className="text-base font-semibold text-[var(--text-primary)]">Top focus areas</h2>
        </div>
        {weaknesses === null ? (
          <div className="grid gap-3 sm:grid-cols-2">
            <Skeleton className="h-20 w-full rounded-2xl" />
            <Skeleton className="h-20 w-full rounded-2xl" />
          </div>
        ) : weaknesses.length > 0 ? (
          <div className="grid gap-3 sm:grid-cols-2">
            {weaknesses.map((w) => (
              <div key={`${w.skill}-${w.subskill}`} className="rounded-2xl border border-[var(--border)] p-4">
                <p className="text-sm font-semibold text-[var(--text-primary)]">{w.label}</p>
                <p className="mt-1 text-xs text-[var(--text-secondary)]">
                  {w.skill} · seen {w.frequency} time{w.frequency === 1 ? "" : "s"}
                </p>
              </div>
            ))}
          </div>
        ) : (
          <EmptyAnalyticsState
            icon={<AlertTriangle className="h-5 w-5" />}
            text="Recurring mistakes will appear after you complete a few graded tasks."
          />
        )}
      </section>
    </div>
  );
}

function SkillBandCard({ skill, band }: { skill: Skill; band?: number }) {
  const meta = skillMeta[skill];
  const tone = toneClasses[meta.tone];
  const Icon = skillIcons[skill];
  const hasBand = band != null;
  const progress = hasBand ? Math.min(1, Math.max(0, band / 9)) : 0;

  return (
    <div className="rounded-3xl border border-[var(--border)] bg-white p-6 shadow-sm shadow-slate-200/40">
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-2.5">
          <span className={`flex h-9 w-9 items-center justify-center rounded-lg ${tone.soft}`}>
            <Icon className="h-5 w-5" />
          </span>
          <h3 className="font-semibold text-[var(--text-primary)]">{meta.label}</h3>
        </div>
        <span className="text-sm font-bold text-[var(--text-primary)]">
          {hasBand ? `Band ${band.toFixed(1)}` : "No data"}
        </span>
      </div>

      <div className="mt-5">
        <ProgressBar value={progress} barClass={hasBand ? tone.bar : "bg-slate-300"} />
      </div>
      <p className="mt-3 text-sm text-[var(--text-secondary)]">
        {hasBand
          ? `${meta.label} is included in your current overall band estimate.`
          : `Complete a ${meta.label} task to add this skill to your estimate.`}
      </p>
    </div>
  );
}

function EmptyAnalyticsState({ icon, text }: { icon: ReactNode; text: string }) {
  return (
    <div className="mt-5 flex items-center gap-3 rounded-2xl border border-dashed border-[var(--border)] bg-slate-50/60 p-6 text-sm text-[var(--text-secondary)]">
      <span className="text-slate-400">{icon}</span>
      {text}
    </div>
  );
}
