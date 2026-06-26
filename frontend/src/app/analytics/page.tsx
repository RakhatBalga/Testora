"use client";

import { type ReactNode, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import {
  Activity,
  AlertTriangle,
  ArrowRight,
  BarChart3,
  Flame,
  ListChecks,
  Target,
  TrendingDown,
  TrendingUp,
} from "lucide-react";
import { useRequireAuth } from "@/shared/auth";
import {
  api,
  type BandGapResult,
  type BandTrajectoryResult,
  type Blocker,
  type DailyPlanTask,
  type HistoryItem,
  type Recommendation,
  type RecurringMistake,
  type Streak,
  type Weakness,
} from "@/shared/api";
import { SKILLS, skillMeta, toneClasses, type Skill } from "@/entities/dashboard";
import { BandTrajectory } from "@/shared/ui/dashboard";
import { PageHeader, ProgressBar, StatTile, skillIcons } from "@/shared/ui/dashboard";
import { LinkButton } from "@/shared/ui";
import { Skeleton } from "@/shared/ui";

const FALLBACK_TARGET_BAND = 7.5;

export default function AnalyticsPage() {
  const { token, ready } = useRequireAuth();
  const [bandGap, setBandGap] = useState<BandGapResult | null>(null);
  const [trajectory, setTrajectory] = useState<BandTrajectoryResult | null>(null);
  const [blockers, setBlockers] = useState<Blocker[] | null>(null);
  const [weaknesses, setWeaknesses] = useState<Weakness[] | null>(null);
  const [dailyPlan, setDailyPlan] = useState<DailyPlanTask[] | null>(null);
  const [recommendations, setRecommendations] = useState<Recommendation[] | null>(null);
  const [recurring, setRecurring] = useState<RecurringMistake[] | null>(null);
  const [streak, setStreak] = useState<Streak | null>(null);
  const [historyItems, setHistoryItems] = useState<HistoryItem[] | null>(null);
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
      api.getBandGap(),
      setBandGap,
      { current: null, target: FALLBACK_TARGET_BAND, gap: null, per_skill: {}, lowest_skill: null, has_data: false }
    );
    settle(api.getBandTrajectory(), setTrajectory, { points: [], delta: null, has_data: false });
    settle(api.getBlockers(), (b) => setBlockers(b.blockers), { blockers: [] });
    settle(api.getWeaknesses(5), (w) => setWeaknesses(w.weaknesses), { weaknesses: [] });
    settle(api.getDailyPlan(undefined, 3), (p) => setDailyPlan(p.plan), { generated_for: "", has_data: false, plan: [] });
    settle(api.getRecommendations(undefined, 4), (r) => setRecommendations(r.recommendations), { recommendations: [] });
    settle(api.getRecurringMistakes(5), (r) => setRecurring(r.recurring), { recurring: [] });
    settle(api.getStreak(), setStreak, { current_streak: 0, active_today: false });
    settle(
      api.getHistory(undefined, "newest"),
      (h) => {
        setHistoryItems(h.items.slice(0, 6));
        setHistoryTotal(h.total);
      },
      { items: [], total: 0 }
    );

    return () => {
      active = false;
    };
  }, [token]);

  const loading =
    bandGap === null ||
    trajectory === null ||
    blockers === null ||
    weaknesses === null ||
    dailyPlan === null ||
    recommendations === null ||
    recurring === null ||
    streak === null ||
    historyItems === null ||
    historyTotal === null;

  const target = bandGap?.target ?? FALLBACK_TARGET_BAND;
  const current = bandGap?.current ?? null;
  const gap = bandGap?.gap ?? null;
  const mainBlocker = blockers?.[0] ?? null;
  const perSkill = useMemo(() => bandGap?.per_skill ?? {}, [bandGap]);
  const topWeaknesses = weaknesses?.slice(0, 3) ?? [];

  if (!ready || !token) return null;

  return (
    <div className="space-y-6">
      <PageHeader
        title="Analytics"
        subtitle="Your evidence-based view of band progress, blockers, and next actions."
        action={
          <LinkButton href="/practice">
            Practice
            <ArrowRight className="h-4 w-4" />
          </LinkButton>
        }
      />

      {error && <p className="rounded-xl bg-red-50 px-4 py-3 text-sm text-red-600">{error}</p>}

      <section className="grid animate-fade-up gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatTile
          label="Current band"
          value={current != null ? current.toFixed(1) : "-"}
          hint={bandGap?.has_data ? "from graded attempts" : "no graded data yet"}
          icon={<TrendingUp className="h-5 w-5" />}
        />
        <StatTile
          label="Gap"
          value={gap != null ? `+${gap.toFixed(1)}` : "-"}
          hint={`target ${target.toFixed(1)}`}
          icon={<Target className="h-5 w-5" />}
          accent="text-amber-500"
        />
        <StatTile
          label="Completed"
          value={loading ? "-" : String(historyTotal ?? 0)}
          hint="saved sessions"
          icon={<ListChecks className="h-5 w-5" />}
          accent="text-emerald-500"
        />
        <StatTile
          label="Streak"
          value={loading ? "-" : `${streak?.current_streak ?? 0}d`}
          hint={streak?.active_today ? "active today" : "practice today"}
          icon={<Flame className="h-5 w-5" />}
          accent="text-amber-500"
        />
      </section>

      <div className="grid gap-6 lg:grid-cols-[minmax(0,1.15fr)_minmax(320px,0.85fr)]">
        <section className="animate-fade-up rounded-2xl border border-[var(--border)] bg-white p-6 shadow-sm shadow-slate-200/40 [animation-delay:80ms]">
          <div className="mb-5 flex items-center gap-2">
            <AlertTriangle className="h-5 w-5 text-amber-500" />
            <h2 className="text-base font-semibold text-[var(--text-primary)]">Main limiter</h2>
          </div>

          {blockers === null ? (
            <Skeleton className="h-32 w-full rounded-2xl" />
          ) : mainBlocker ? (
            <div>
              <div className="flex flex-wrap items-center gap-2">
                <span className="rounded-md bg-slate-100 px-2 py-0.5 text-xs font-semibold capitalize text-[var(--text-secondary)]">
                  {mainBlocker.skill}
                </span>
                <span className="rounded-md bg-amber-50 px-2 py-0.5 text-xs font-semibold text-amber-600">
                  Cap {mainBlocker.band_cap.toFixed(1)}
                </span>
              </div>
              <h3 className="mt-3 text-xl font-bold text-[var(--text-primary)]">
                {mainBlocker.criterion}
              </h3>
              <p className="mt-2 max-w-3xl text-sm leading-6 text-[var(--text-secondary)]">
                {mainBlocker.explanation}
              </p>

              {topWeaknesses.length > 0 && (
                <div className="mt-5 flex flex-wrap gap-2">
                  {topWeaknesses.map((w) => (
                    <span
                      key={`${w.skill}-${w.subskill}`}
                      className="rounded-full border border-[var(--border)] px-3 py-1 text-xs font-medium text-[var(--text-secondary)]"
                    >
                      {w.label}
                    </span>
                  ))}
                </div>
              )}

              <LinkButton href={mainBlocker.fix_href} className="mt-6">
                Practice this
                <ArrowRight className="h-4 w-4" />
              </LinkButton>
            </div>
          ) : (
            <EmptyAnalyticsState
              icon={<AlertTriangle className="h-5 w-5" />}
              text="Complete a Writing or Speaking task and your main limiter will appear here."
            />
          )}
        </section>

        <section className="animate-fade-up rounded-2xl border border-[var(--border)] bg-white p-6 shadow-sm shadow-slate-200/40 [animation-delay:120ms]">
          <div className="mb-4 flex items-center gap-2">
            <ListChecks className="h-5 w-5 text-[var(--brand)]" />
            <h2 className="text-base font-semibold text-[var(--text-primary)]">Recommended next</h2>
          </div>

          {dailyPlan === null || recommendations === null ? (
            <div className="space-y-2.5">
              {[0, 1, 2].map((i) => (
                <Skeleton key={i} className="h-16 w-full rounded-xl" />
              ))}
            </div>
          ) : dailyPlan.length > 0 ? (
            <div className="space-y-2.5">
              {dailyPlan.map((task, index) => (
                <ActionRow
                  key={task.id}
                  href={task.href}
                  title={task.title}
                  detail={`${task.estimated_minutes} min - ${sourceLabel(task.source)}`}
                  index={index + 1}
                />
              ))}
            </div>
          ) : recommendations.length > 0 ? (
            <div className="space-y-2.5">
              {recommendations.slice(0, 3).map((rec, index) => (
                <ActionRow
                  key={rec.id}
                  href={rec.href}
                  title={rec.title}
                  detail={`${rec.estimated_impact} impact - ${rec.estimated_minutes} min`}
                  index={index + 1}
                />
              ))}
            </div>
          ) : (
            <EmptyAnalyticsState
              icon={<ListChecks className="h-5 w-5" />}
              text="Recommendations will appear after your first graded attempt."
            />
          )}
        </section>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <section className="animate-fade-up rounded-2xl border border-[var(--border)] bg-white p-6 shadow-sm shadow-slate-200/40 [animation-delay:160ms] sm:p-7 lg:col-span-2">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <h2 className="text-base font-semibold text-[var(--text-primary)]">Band trajectory</h2>
            {trajectory?.has_data && trajectory.delta != null && (
              <span
                className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-semibold ${
                  trajectory.delta >= 0 ? "bg-emerald-50 text-emerald-600" : "bg-red-50 text-red-600"
                }`}
              >
                {trajectory.delta >= 0 ? <TrendingUp className="h-3.5 w-3.5" /> : <TrendingDown className="h-3.5 w-3.5" />}
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
              text="Complete a couple of graded tasks and your band trajectory will plot here."
            />
          )}
        </section>

        <section className="animate-fade-up rounded-2xl border border-[var(--border)] bg-white p-6 shadow-sm shadow-slate-200/40 [animation-delay:200ms]">
          <div className="mb-4 flex items-center gap-2">
            <Activity className="h-5 w-5 text-[var(--brand)]" />
            <h2 className="text-base font-semibold text-[var(--text-primary)]">Recurring patterns</h2>
          </div>
          {recurring === null ? (
            <div className="space-y-2.5">
              {[0, 1, 2].map((i) => (
                <Skeleton key={i} className="h-14 w-full rounded-xl" />
              ))}
            </div>
          ) : recurring.length > 0 ? (
            <div className="space-y-2.5">
              {recurring.map((item) => (
                <div key={`${item.skill}-${item.subskill}`} className="rounded-xl border border-[var(--border)] px-4 py-3">
                  <p className="text-sm font-semibold text-[var(--text-primary)]">{item.label}</p>
                  <p className="mt-0.5 text-xs capitalize text-[var(--text-secondary)]">
                    {item.skill} - {item.occurrences} times
                  </p>
                </div>
              ))}
            </div>
          ) : (
            <EmptyAnalyticsState
              icon={<Activity className="h-5 w-5" />}
              text="Recurring mistakes will appear after a few graded tasks."
            />
          )}
        </section>
      </div>

      <section className="grid animate-fade-up gap-4 [animation-delay:240ms] sm:grid-cols-2 lg:grid-cols-4">
        {SKILLS.map((skill) => (
          <SkillBandCard key={skill} skill={skill} band={perSkill[skill]} />
        ))}
      </section>

      <section className="animate-fade-up rounded-2xl border border-[var(--border)] bg-white p-6 shadow-sm shadow-slate-200/40 [animation-delay:280ms]">
        <div className="mb-4 flex items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <BarChart3 className="h-5 w-5 text-[var(--brand)]" />
            <h2 className="text-base font-semibold text-[var(--text-primary)]">Recent activity</h2>
          </div>
          <Link href="/practice" className="text-sm font-semibold text-[var(--brand)]">
            Practice more
          </Link>
        </div>

        {historyItems === null ? (
          <div className="space-y-2.5">
            {[0, 1, 2].map((i) => (
              <Skeleton key={i} className="h-14 w-full rounded-xl" />
            ))}
          </div>
        ) : historyItems.length > 0 ? (
          <div className="grid gap-2.5 md:grid-cols-2">
            {historyItems.map((item) => (
              <HistoryRow key={item.id} item={item} />
            ))}
          </div>
        ) : (
          <EmptyAnalyticsState
            icon={<BarChart3 className="h-5 w-5" />}
            text="Your completed practice sessions will appear here."
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
    <Link
      href={meta.href}
      className="group rounded-2xl border border-[var(--border)] bg-white p-5 shadow-sm shadow-slate-200/40 transition-colors hover:border-slate-300 hover:bg-slate-50"
    >
      <div className="flex items-center justify-between gap-3">
        <span className={`flex h-9 w-9 items-center justify-center rounded-lg ${tone.soft}`}>
          <Icon className="h-5 w-5" />
        </span>
        <span className="text-sm font-bold text-[var(--text-primary)]">
          {hasBand ? `Band ${band.toFixed(1)}` : "No data"}
        </span>
      </div>

      <h3 className="mt-4 font-semibold text-[var(--text-primary)]">{meta.label}</h3>
      <div className="mt-4">
        <ProgressBar value={progress} barClass={hasBand ? tone.bar : "bg-slate-300"} />
      </div>
      <p className="mt-3 flex items-center gap-1.5 text-sm font-semibold text-[var(--brand)]">
        Practice
        <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5" />
      </p>
    </Link>
  );
}

function ActionRow({
  href,
  title,
  detail,
  index,
}: {
  href: string;
  title: string;
  detail: string;
  index: number;
}) {
  return (
    <Link
      href={href}
      className="group flex items-start gap-3 rounded-xl border border-[var(--border)] px-4 py-3 transition-colors hover:border-slate-300 hover:bg-slate-50"
    >
      <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-[var(--brand)]/[0.1] text-xs font-bold text-[var(--brand)]">
        {index}
      </span>
      <span className="min-w-0 flex-1">
        <span className="block text-sm font-semibold text-[var(--text-primary)]">{title}</span>
        <span className="mt-0.5 block text-xs text-[var(--text-secondary)]">{detail}</span>
      </span>
      <ArrowRight className="mt-1 h-4 w-4 shrink-0 text-slate-300 transition-transform group-hover:translate-x-0.5 group-hover:text-[var(--brand)]" />
    </Link>
  );
}

function HistoryRow({ item }: { item: HistoryItem }) {
  return (
    <Link
      href={item.href}
      className="group flex items-center justify-between gap-3 rounded-xl border border-[var(--border)] px-4 py-3 transition-colors hover:border-slate-300 hover:bg-slate-50"
    >
      <span className="min-w-0">
        <span className="block truncate text-sm font-semibold text-[var(--text-primary)]">
          {item.title}
        </span>
        <span className="mt-0.5 block text-xs capitalize text-[var(--text-secondary)]">
          {item.skill} - {formatDate(item.created_at)}
        </span>
      </span>
      <span className="shrink-0 rounded-lg bg-slate-100 px-2.5 py-1 text-xs font-semibold text-[var(--text-secondary)]">
        {item.band != null ? `Band ${item.band.toFixed(1)}` : item.score != null && item.total != null ? `${item.score}/${item.total}` : item.status}
      </span>
    </Link>
  );
}

function EmptyAnalyticsState({ icon, text }: { icon: ReactNode; text: string }) {
  return (
    <div className="flex items-center gap-3 rounded-2xl border border-dashed border-[var(--border)] bg-slate-50/60 p-6 text-sm text-[var(--text-secondary)]">
      <span className="text-slate-400">{icon}</span>
      {text}
    </div>
  );
}

function formatDate(value: string | null): string {
  if (!value) return "No date";
  return new Date(value).toLocaleDateString();
}

function sourceLabel(source: DailyPlanTask["source"]): string {
  const labels: Record<DailyPlanTask["source"], string> = {
    blocker: "blocker",
    band_gap: "band gap",
    weakness: "weakness",
    last_activity: "stale skill",
    cold_start: "first step",
  };
  return labels[source];
}
