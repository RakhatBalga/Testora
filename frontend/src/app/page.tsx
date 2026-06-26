"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  ArrowRight,
  ArrowUpRight,
  Flame,
  TrendingUp,
  TrendingDown,
  Minus,
  AlertTriangle,
  ListChecks,
  Activity,
} from "lucide-react";
import { useAuth } from "@/lib/auth";
import Landing from "@/components/landing/Landing";
import { api, type Blocker, type Weakness, type BandGapResult, type BandTrajectoryResult, type DailyPlanTask, type Streak } from "@/lib/api";
import { greeting, type ProgressMovement } from "@/lib/coach";
import { BandTrajectory } from "@/components/dashboard/BandTrajectory";

/** Target band source. Future: profiles/goals.target_band. */
const TARGET_BAND = 7.5;

export default function HomePage() {
  const { token, username, ready } = useAuth();
  if (!ready) return null;
  return token ? <CoachDashboard username={username} /> : <Landing />;
}

function CoachDashboard({ username }: { username: string | null }) {
  const name = username ?? "there";
  // Real analytics (Mistake Memory + Band Gap engines).
  const [bandGap, setBandGap] = useState<BandGapResult | null>(null);
  const [blockers, setBlockers] = useState<Blocker[] | null>(null);
  const [weaknesses, setWeaknesses] = useState<Weakness[] | null>(null);
  const [trajectory, setTrajectory] = useState<BandTrajectoryResult | null>(null);
  const [recentMovement, setRecentMovement] = useState<ProgressMovement[] | null>(null);
  const [todaysPlan, setTodaysPlan] = useState<DailyPlanTask[] | null>(null);
  const [streak, setStreak] = useState<Streak | null>(null);

  useEffect(() => {
    let active = true;

    // Each widget resolves independently: one failing endpoint must not blank
    // out the whole dashboard (which would falsely show a "no data" state to a
    // user who actually has data).
    const settle = <T,>(p: Promise<T>, apply: (v: T) => void, fallback: T) => {
      p.then((v) => active && apply(v)).catch(() => active && apply(fallback));
    };

    settle(
      api.getBandGap(TARGET_BAND),
      setBandGap,
      { current: null, target: TARGET_BAND, gap: null, per_skill: {}, lowest_skill: null, has_data: false }
    );
    settle(api.getBlockers(TARGET_BAND), (b) => setBlockers(b.blockers), { blockers: [] });
    settle(api.getWeaknesses(3), (w) => setWeaknesses(w.weaknesses), { weaknesses: [] });
    settle(api.getBandTrajectory(), setTrajectory, { points: [], delta: null, has_data: false });
    settle(api.getDailyPlan(TARGET_BAND, 3), (p) => setTodaysPlan(p.plan), { generated_for: "", has_data: false, plan: [] });
    settle(api.getStreak(), setStreak, { current_streak: 0, active_today: false });

    // Recent movement = real Before→After of the most recent graded Writing attempt.
    (async () => {
      try {
        const subs = await api.listWritingSubmissions();
        const latest = subs.find((s) => s.status === "graded" && s.band != null);
        if (!latest) {
          if (active) setRecentMovement([]);
          return;
        }
        const impact = await api.getProgressImpact("writing", latest.id);
        if (!active) return;
        if (!impact.has_previous || !impact.criteria) {
          setRecentMovement([]);
          return;
        }
        setRecentMovement(
          impact.criteria.slice(0, 4).map((c) => ({
            label: `Writing — ${c.name}`,
            from: c.from,
            to: c.to,
            direction: c.direction,
          }))
        );
      } catch {
        if (active) setRecentMovement([]);
      }
    })();

    return () => {
      active = false;
    };
  }, []);

  const loading = bandGap === null;
  const hasData = !!bandGap?.has_data;
  const current = bandGap?.current ?? null;
  const target = bandGap?.target ?? TARGET_BAND;
  const gapValue = bandGap?.gap ?? null;
  const mainBlocker = blockers?.[0] ?? null;
  const topWeaknesses = weaknesses?.slice(0, 3) ?? [];
  const nextTask = todaysPlan?.[0] ?? null;
  const primaryActionHref = mainBlocker?.fix_href ?? nextTask?.href ?? "/practice";

  return (
    <div className="space-y-6">
      <div className="flex animate-fade-up items-center justify-between">
        <p className="text-sm font-medium text-[var(--text-secondary)]">
          {greeting()}, <span className="text-[var(--text-primary)]">{name}</span>
        </p>
        {streak && streak.current_streak > 0 && (
          <span className="inline-flex items-center gap-1.5 rounded-full border border-[var(--border)] bg-white px-3 py-1.5 text-xs font-semibold text-[var(--text-secondary)]">
            <Flame className="h-3.5 w-3.5 text-amber-500" />
            {streak.current_streak}-day streak
          </span>
        )}
      </div>

      <section className="animate-fade-up rounded-2xl border border-[var(--border)] bg-white p-5 shadow-sm shadow-slate-200/40 [animation-delay:60ms] sm:p-6">
        <div className="flex flex-col gap-5 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-[var(--text-secondary)]">
              Dashboard
            </p>
            <h1 className="mt-1 text-2xl font-bold tracking-tight text-[var(--text-primary)]">
              IELTS progress
            </h1>
          </div>
          <Link
            href={primaryActionHref}
            className="inline-flex h-11 items-center justify-center gap-2 rounded-xl bg-[var(--brand)] px-4 text-sm font-semibold text-white shadow-sm shadow-[var(--brand)]/25 transition-colors hover:bg-[var(--brand-dark)]"
          >
            {hasData ? "Continue practice" : "Start practising"}
            <ArrowRight className="h-4 w-4" />
          </Link>
        </div>

        <div className="mt-6 grid gap-5 border-t border-[var(--border)] pt-5 sm:grid-cols-3">
          <Metric label="Current band" value={current != null ? current.toFixed(1) : "—"} hint={hasData ? "from graded attempts" : "no data yet"} />
          <Metric label="Target" value={target.toFixed(1)} hint="goal band" />
          <Metric label="Gap" value={gapValue != null ? `+${gapValue.toFixed(1)}` : "—"} hint="bands remaining" />
        </div>

        <div className="mt-5 h-2 overflow-hidden rounded-full bg-slate-100">
          <div
            className="h-full rounded-full bg-[var(--brand)] transition-[width] duration-700 ease-out"
            style={{
              width: `${hasData && current != null ? Math.min(100, (current / target) * 100) : 0}%`,
            }}
          />
        </div>
      </section>

      <div className="grid gap-6 lg:grid-cols-[minmax(0,1.45fr)_minmax(320px,0.85fr)]">
        <section className="animate-fade-up rounded-2xl border border-[var(--border)] bg-white p-6 shadow-sm shadow-slate-200/40 [animation-delay:100ms]">
          <div className="flex items-center gap-2">
            <AlertTriangle className="h-5 w-5 text-amber-500" />
            <h2 className="text-base font-semibold text-[var(--text-primary)]">Main focus</h2>
          </div>

          {loading ? (
            <div className="mt-5">
              <SkeletonCard />
            </div>
          ) : mainBlocker ? (
            <div className="mt-5">
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
                <div className="mt-5 border-t border-[var(--border)] pt-4">
                  <p className="text-xs font-semibold uppercase tracking-wide text-[var(--text-secondary)]">
                    Related patterns
                  </p>
                  <div className="mt-3 flex flex-wrap gap-2">
                    {topWeaknesses.map((w) => (
                      <span
                        key={`${w.skill}-${w.subskill}`}
                        className="rounded-full border border-[var(--border)] px-3 py-1 text-xs font-medium text-[var(--text-secondary)]"
                      >
                        {w.label}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              <Link
                href={mainBlocker.fix_href}
                className="mt-6 inline-flex h-10 items-center justify-center gap-2 rounded-xl bg-[var(--brand)] px-4 text-sm font-semibold text-white transition-colors hover:bg-[var(--brand-dark)]"
              >
                Practice this
                <ArrowRight className="h-4 w-4" />
              </Link>
            </div>
          ) : (
            <div className="mt-5">
              <EmptyState
                icon={<AlertTriangle className="h-5 w-5" />}
                text="Complete a Writing task and I'll identify the single thing most likely to cap your band."
              />
            </div>
          )}
        </section>

        <section className="animate-fade-up rounded-2xl border border-[var(--border)] bg-white p-6 shadow-sm shadow-slate-200/40 [animation-delay:140ms]">
          <div className="mb-4 flex items-center gap-2">
            <ListChecks className="h-5 w-5 text-[var(--brand)]" />
            <h2 className="text-base font-semibold text-[var(--text-primary)]">Today&apos;s plan</h2>
          </div>
          {todaysPlan === null ? (
            <div className="space-y-2.5">
              <div className="h-16 animate-pulse rounded-2xl bg-slate-50" />
              <div className="h-16 animate-pulse rounded-2xl bg-slate-50" />
              <div className="h-16 animate-pulse rounded-2xl bg-slate-50" />
            </div>
          ) : todaysPlan.length > 0 ? (
            <ol className="space-y-2.5">
              {todaysPlan.map((task, i) => (
                <li key={task.id}>
                  <Link
                    href={task.href}
                    className="group flex items-start gap-3 rounded-2xl border border-[var(--border)] p-3.5 transition-colors hover:border-slate-300 hover:bg-slate-50"
                  >
                    <span className="flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-full bg-[var(--brand)]/[0.1] text-xs font-bold text-[var(--brand)]">
                      {i + 1}
                    </span>
                    <span className="min-w-0 flex-1">
                      <span className="block text-sm font-semibold text-[var(--text-primary)]">{task.title}</span>
                      {task.detail && (
                        <span className="mt-0.5 block text-xs text-[var(--text-secondary)]">
                          {task.detail}
                          {task.estimated_minutes ? ` · ${task.estimated_minutes} min` : ""}
                        </span>
                      )}
                    </span>
                    <ArrowUpRight className="h-4 w-4 flex-shrink-0 text-slate-300 transition-colors group-hover:text-[var(--brand)]" />
                  </Link>
                </li>
              ))}
            </ol>
          ) : (
            <EmptyState
              icon={<ListChecks className="h-5 w-5" />}
              text="Complete a task and I'll build tomorrow's plan from your weak spots."
            />
          )}
        </section>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <section className="animate-fade-up rounded-2xl border border-[var(--border)] bg-white p-6 shadow-sm shadow-slate-200/40 [animation-delay:180ms] sm:p-7 lg:col-span-2">
          <div className="flex items-center justify-between">
            <h2 className="text-base font-semibold text-[var(--text-primary)]">Band trajectory</h2>
            {trajectory?.has_data && trajectory.delta != null && (
              <span
                className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-semibold ${
                  trajectory.delta >= 0 ? "bg-emerald-50 text-emerald-600" : "bg-red-50 text-red-600"
                }`}
              >
                {trajectory.delta >= 0 ? <TrendingUp className="h-3.5 w-3.5" /> : <TrendingDown className="h-3.5 w-3.5" />}
                {trajectory.delta >= 0 ? "+" : ""}
                {trajectory.delta.toFixed(1)} since you started
              </span>
            )}
          </div>
          {loading ? (
            <div className="mt-5 h-60 animate-pulse rounded-2xl bg-slate-50" />
          ) : trajectory && trajectory.points.length > 1 ? (
            <BandTrajectory points={trajectory.points} target={target} />
          ) : (
            <EmptyState
              icon={<TrendingUp className="h-5 w-5" />}
              text="Complete a couple of graded tasks and your band trajectory will plot here."
            />
          )}
        </section>

        <section className="animate-fade-up rounded-2xl border border-[var(--border)] bg-white p-6 shadow-sm shadow-slate-200/40 [animation-delay:220ms]">
          <h2 className="text-base font-semibold text-[var(--text-primary)]">Recent movement</h2>
          <p className="mt-1 text-xs text-[var(--text-secondary)]">Change since your last Writing attempt</p>
          {recentMovement === null ? (
            <div className="mt-4 space-y-2.5">
              <div className="h-11 animate-pulse rounded-xl bg-slate-50" />
              <div className="h-11 animate-pulse rounded-xl bg-slate-50" />
              <div className="h-11 animate-pulse rounded-xl bg-slate-50" />
            </div>
          ) : recentMovement.length > 0 ? (
            <div className="mt-4 space-y-2.5">
              {recentMovement.map((m) => (
                <MovementRow key={m.label} movement={m} />
              ))}
            </div>
          ) : (
            <div className="mt-4">
              <EmptyState
                icon={<Activity className="h-5 w-5" />}
                text="Submit a second Writing task to see how each criterion moved."
              />
            </div>
          )}
        </section>
      </div>
    </div>
  );
}

function Metric({
  label,
  value,
  hint,
}: {
  label: string;
  value: string;
  hint?: string;
}) {
  return (
    <div>
      <p className="text-xs font-medium uppercase tracking-wide text-[var(--text-secondary)]">{label}</p>
      <p className="mt-1 text-3xl font-extrabold tracking-tight text-[var(--text-primary)]">{value}</p>
      {hint && <p className="mt-0.5 text-xs text-[var(--text-secondary)]">{hint}</p>}
    </div>
  );
}

function EmptyState({ icon, text }: { icon: React.ReactNode; text: string }) {
  return (
    <div className="flex items-center gap-3 rounded-2xl border border-dashed border-[var(--border)] bg-white p-6 text-sm text-[var(--text-secondary)]">
      <span className="text-slate-400">{icon}</span>
      {text}
    </div>
  );
}

function SkeletonCard() {
  return <div className="h-24 animate-pulse rounded-2xl border border-[var(--border)] bg-slate-50" />;
}

function MovementRow({ movement }: { movement: ProgressMovement }) {
  const { label, from, to, direction } = movement;
  const hasData = from != null && to != null;
  const tone =
    direction === "up"
      ? "text-emerald-600"
      : direction === "down"
        ? "text-red-600"
        : "text-[var(--text-secondary)]";
  const Icon = direction === "up" ? TrendingUp : direction === "down" ? TrendingDown : Minus;

  return (
    <div className="flex items-center justify-between rounded-xl bg-slate-50 px-3.5 py-2.5">
      <span className="text-sm font-medium text-[var(--text-primary)]">{label}</span>
      <span className={`inline-flex items-center gap-1.5 text-sm font-semibold ${tone}`}>
        <Icon className="h-4 w-4" />
        {hasData ? `${from!.toFixed(1)} → ${to!.toFixed(1)}` : "No change"}
      </span>
    </div>
  );
}
