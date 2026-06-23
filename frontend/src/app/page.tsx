"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  ArrowRight,
  ArrowUpRight,
  Flame,
  Target,
  TrendingUp,
  TrendingDown,
  Minus,
  CalendarClock,
  AlertTriangle,
  CircleCheck,
  ListChecks,
  Activity,
} from "lucide-react";
import { useAuth } from "@/lib/auth";
import Landing from "@/components/landing/Landing";
import { api, type Blocker, type Weakness, type BandGapResult } from "@/lib/api";
import { coachDashboard, daysUntil, greeting, type ProgressMovement } from "@/lib/coach";
import { Ring } from "@/components/dashboard/widgets";
import { BandTrajectory } from "@/components/dashboard/BandTrajectory";
import { WeaknessCard } from "@/components/dashboard/WeaknessCard";
import { BlockerCard } from "@/components/dashboard/BlockerCard";

/** Target band source. Future: profiles/goals.target_band. */
const TARGET_BAND = 7.5;

export default function HomePage() {
  const { token, username, ready } = useAuth();
  if (!ready) return null;
  return token ? <CoachDashboard username={username} /> : <Landing />;
}

function CoachDashboard({ username }: { username: string | null }) {
  const name = username ?? "there";
  // Out-of-scope sections stay on mock for now (Phase 1 dashboard).
  const { todaysPlan, recentMovement, trajectory, streakDays, gap: mockGap } = coachDashboard;

  // Real analytics (Mistake Memory + Band Gap engines).
  const [bandGap, setBandGap] = useState<BandGapResult | null>(null);
  const [blockers, setBlockers] = useState<Blocker[] | null>(null);
  const [weaknesses, setWeaknesses] = useState<Weakness[] | null>(null);

  useEffect(() => {
    let active = true;
    Promise.all([
      api.getBandGap(TARGET_BAND),
      api.getBlockers(TARGET_BAND),
      api.getWeaknesses(6),
    ])
      .then(([g, b, w]) => {
        if (!active) return;
        setBandGap(g);
        setBlockers(b.blockers);
        setWeaknesses(w.weaknesses);
      })
      .catch(() => {
        if (!active) return;
        setBandGap({ current: null, target: TARGET_BAND, gap: null, per_skill: {}, lowest_skill: null, has_data: false });
        setBlockers([]);
        setWeaknesses([]);
      });
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
  const daysLeft = daysUntil(mockGap.examDate);

  return (
    <div className="space-y-8">
      {/* greeting + streak (small secondary badge) */}
      <div className="flex animate-fade-up items-center justify-between">
        <p className="text-sm font-medium text-[var(--text-secondary)]">
          {greeting()}, <span className="text-[var(--text-primary)]">{name}</span>
        </p>
        <span className="inline-flex items-center gap-1.5 rounded-full border border-[var(--border)] bg-white px-3 py-1.5 text-xs font-semibold text-[var(--text-secondary)]">
          <Flame className="h-3.5 w-3.5 text-amber-500" />
          {streakDays}-day streak
        </span>
      </div>

      {/* SECTION 1 — Coach hero card */}
      <section className="relative animate-fade-up overflow-hidden rounded-3xl bg-[var(--brand)] p-7 text-white shadow-[0_20px_60px_-20px_rgba(37,99,235,0.45)] [animation-delay:60ms] sm:p-9">
        <div
          className="pointer-events-none absolute inset-0 opacity-[0.12]"
          style={{
            backgroundImage: "radial-gradient(circle at 1px 1px, white 1px, transparent 0)",
            backgroundSize: "24px 24px",
          }}
        />
        <div className="pointer-events-none absolute -right-16 -top-20 h-64 w-64 rounded-full bg-[var(--brand-light)]/40 blur-3xl" />

        <div className="relative flex flex-col items-start gap-8 lg:flex-row lg:items-center lg:justify-between">
          <div className="max-w-2xl">
            <span className="inline-flex items-center gap-1.5 rounded-full bg-white/15 px-3 py-1 text-xs font-semibold uppercase tracking-wide">
              <Target className="h-3.5 w-3.5" />
              Your coach
            </span>

            {hasData && current != null ? (
              <>
                <p className="mt-4 text-[1.35rem] font-bold leading-snug sm:text-[1.6rem]">
                  {name}, you&apos;re estimated at{" "}
                  <span className="underline decoration-white/40 underline-offset-4">
                    Band {current.toFixed(1)}
                  </span>{" "}
                  — your target is Band {target.toFixed(1)}.
                </p>
                <p className="mt-3 text-[0.975rem] leading-relaxed text-white/80">
                  {mainBlocker ? (
                    <>
                      Your biggest blocker is{" "}
                      <strong className="font-semibold text-white">
                        {mainBlocker.criterion} in {mainBlocker.skill}
                      </strong>
                      . {mainBlocker.explanation}
                    </>
                  ) : (
                    "Keep submitting tasks and I'll pinpoint exactly what's holding your band back."
                  )}
                </p>
              </>
            ) : (
              <p className="mt-4 max-w-xl text-[1.2rem] font-bold leading-snug sm:text-[1.5rem]">
                {name}, complete a Writing task and I&apos;ll estimate your band and find your
                biggest blocker.
              </p>
            )}

            <Link
              href={mainBlocker?.fix_href ?? todaysPlan[0]?.href ?? "/practice"}
              className="mt-6 inline-flex h-12 items-center gap-2 rounded-xl bg-white px-5 text-sm font-semibold text-[var(--brand)] transition-transform duration-200 hover:-translate-y-0.5"
            >
              {hasData ? "Start today's task" : "Start practising"}
              <ArrowRight className="h-4 w-4" />
            </Link>
          </div>

          <Ring value={hasData && current != null ? Math.min(1, current / target) : 0}>
            <span className="text-3xl font-extrabold">{current != null ? current.toFixed(1) : "—"}</span>
            <span className="text-xs text-white/70">of {target.toFixed(1)}</span>
          </Ring>
        </div>
      </section>

      {/* SECTION 2 — Band gap strip */}
      <section className="grid animate-fade-up gap-4 [animation-delay:100ms] sm:grid-cols-2 lg:grid-cols-4">
        <GapCard label="Current Band" value={current != null ? current.toFixed(1) : "—"} icon={<CircleCheck className="h-5 w-5" />} hint={hasData ? "estimated from your attempts" : "no attempts yet"} />
        <GapCard label="Target Band" value={target.toFixed(1)} icon={<Target className="h-5 w-5" />} accent="text-[var(--brand)]" />
        <GapCard label="Gap Remaining" value={gapValue != null ? `+${gapValue.toFixed(1)}` : "—"} icon={<TrendingUp className="h-5 w-5" />} accent="text-amber-500" hint="bands to your target" />
        <GapCard
          label="Exam Countdown"
          value={daysLeft != null ? `${daysLeft} days` : "Not set"}
          icon={<CalendarClock className="h-5 w-5" />}
          accent="text-sky-500"
          hint={daysLeft != null ? "until your exam" : "add your exam date"}
        />
      </section>

      <div className="grid gap-6 lg:grid-cols-3">
        {/* SECTION 3 — What's blocking you (real blockers) */}
        <section className="animate-fade-up [animation-delay:140ms] lg:col-span-2">
          <div className="mb-4 flex items-center gap-2">
            <AlertTriangle className="h-5 w-5 text-amber-500" />
            <h2 className="text-base font-semibold text-[var(--text-primary)]">What&apos;s blocking you</h2>
          </div>
          <div className="grid gap-4">
            {loading ? (
              <SkeletonCard />
            ) : blockers && blockers.length > 0 ? (
              blockers.map((b) => <BlockerCard key={`${b.skill}-${b.criterion}`} blocker={b} />)
            ) : (
              <EmptyState
                icon={<AlertTriangle className="h-5 w-5" />}
                text="Submit a Writing task to reveal what's capping your band."
              />
            )}
          </div>
        </section>

        {/* SECTION 4 — Today's plan (mock, out of scope) */}
        <section className="animate-fade-up rounded-3xl border border-[var(--border)] bg-white p-6 shadow-sm shadow-slate-200/40 [animation-delay:180ms]">
          <div className="mb-4 flex items-center gap-2">
            <ListChecks className="h-5 w-5 text-[var(--brand)]" />
            <h2 className="text-base font-semibold text-[var(--text-primary)]">Today&apos;s plan</h2>
          </div>
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
                        {task.estimatedMinutes ? ` · ${task.estimatedMinutes} min` : ""}
                      </span>
                    )}
                  </span>
                  <ArrowUpRight className="h-4 w-4 flex-shrink-0 text-slate-300 transition-colors group-hover:text-[var(--brand)]" />
                </Link>
              </li>
            ))}
          </ol>
        </section>
      </div>

      {/* SECTION 5 — Top weaknesses (real, Mistake Memory) */}
      <section className="animate-fade-up [animation-delay:200ms]">
        <div className="mb-4 flex items-center gap-2">
          <Activity className="h-5 w-5 text-[var(--brand)]" />
          <h2 className="text-base font-semibold text-[var(--text-primary)]">Your top weaknesses</h2>
        </div>
        {loading ? (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            <SkeletonCard />
            <SkeletonCard />
            <SkeletonCard />
          </div>
        ) : weaknesses && weaknesses.length > 0 ? (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {weaknesses.map((w) => (
              <WeaknessCard key={`${w.skill}-${w.subskill}`} weakness={w} />
            ))}
          </div>
        ) : (
          <EmptyState
            icon={<Activity className="h-5 w-5" />}
            text="Your recurring mistakes will appear here once you've completed a few tasks."
          />
        )}
      </section>

      <div className="grid gap-6 lg:grid-cols-3">
        {/* SECTION 6 — Band trajectory (mock, out of scope) */}
        <section className="animate-fade-up rounded-3xl border border-[var(--border)] bg-white p-6 shadow-sm shadow-slate-200/40 [animation-delay:240ms] sm:p-7 lg:col-span-2">
          <div className="flex items-center justify-between">
            <h2 className="text-base font-semibold text-[var(--text-primary)]">Band trajectory</h2>
            <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-50 px-3 py-1 text-xs font-semibold text-emerald-600">
              <TrendingUp className="h-3.5 w-3.5" />
              +{(trajectory[trajectory.length - 1].band - trajectory[0].band).toFixed(1)} since you started
            </span>
          </div>
          <BandTrajectory points={trajectory} target={target} />
        </section>

        {/* SECTION 7 — Recent movement (mock, out of scope) */}
        <section className="animate-fade-up rounded-3xl border border-[var(--border)] bg-white p-6 shadow-sm shadow-slate-200/40 [animation-delay:280ms]">
          <h2 className="text-base font-semibold text-[var(--text-primary)]">Recent movement</h2>
          <p className="mt-1 text-xs text-[var(--text-secondary)]">Change since your last attempts</p>
          <div className="mt-4 space-y-2.5">
            {recentMovement.map((m) => (
              <MovementRow key={m.label} movement={m} />
            ))}
          </div>
        </section>
      </div>
    </div>
  );
}

function GapCard({
  label,
  value,
  icon,
  hint,
  accent = "text-[var(--text-secondary)]",
}: {
  label: string;
  value: string;
  icon: React.ReactNode;
  hint?: string;
  accent?: string;
}) {
  return (
    <div className="rounded-2xl border border-[var(--border)] bg-white p-5 shadow-sm shadow-slate-200/40">
      <div className="flex items-center justify-between">
        <p className="text-sm font-medium text-[var(--text-secondary)]">{label}</p>
        <span className={accent}>{icon}</span>
      </div>
      <p className="mt-2 text-3xl font-extrabold tracking-tight text-[var(--text-primary)]">{value}</p>
      {hint && <p className="mt-1 text-xs text-[var(--text-secondary)]">{hint}</p>}
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
