"use client";

import Link from "next/link";
import { ArrowRight, Flame, Target, Clock, CheckCircle2, Trophy } from "lucide-react";
import { useAuth } from "@/lib/auth";
import Landing from "@/components/landing/Landing";
import {
  SKILLS,
  skillMeta,
  toneClasses,
  learner,
  recentActivity,
  leaderboard,
  greeting,
} from "@/lib/dashboard";
import { Ring, ProgressBar, SkillRow, StatTile, skillIcons } from "@/components/dashboard/widgets";

export default function HomePage() {
  const { token, username, ready } = useAuth();
  if (!ready) return null;
  return token ? <Dashboard username={username} /> : <Landing />;
}

function Dashboard({ username }: { username: string | null }) {
  const name = username ?? "there";

  return (
    <div className="space-y-8">
      {/* top stat tiles */}
      <div className="grid animate-fade-up gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatTile
          label="Target Band"
          value={learner.targetBand.toFixed(1)}
          hint="IELTS Academic"
          icon={<Target className="h-5 w-5" />}
        />
        <StatTile
          label="Current Level"
          value={learner.currentBand.toFixed(1)}
          hint={`+${(learner.currentBand - 5).toFixed(1)} since you started`}
          icon={<CheckCircle2 className="h-5 w-5" />}
          accent="text-emerald-500"
        />
        <StatTile
          label="Weekly Goal"
          value={`${learner.weeklyGoalHours}h`}
          hint={`${learner.weeklyDoneHours}h done this week`}
          icon={<Clock className="h-5 w-5" />}
          accent="text-sky-500"
        />
        <StatTile
          label="Study Streak"
          value={`${learner.streakDays} days`}
          hint="Keep it going!"
          icon={<Flame className="h-5 w-5" />}
          accent="text-amber-500"
        />
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        {/* hero card */}
        <section className="relative animate-fade-up overflow-hidden rounded-3xl bg-[var(--brand)] p-7 text-white shadow-[0_20px_60px_-20px_rgba(37,99,235,0.45)] [animation-delay:60ms] lg:col-span-2 sm:p-9">
          <div
            className="pointer-events-none absolute inset-0 opacity-[0.12]"
            style={{
              backgroundImage: "radial-gradient(circle at 1px 1px, white 1px, transparent 0)",
              backgroundSize: "24px 24px",
            }}
          />
          <div className="pointer-events-none absolute -right-16 -top-20 h-64 w-64 rounded-full bg-[var(--brand-light)]/40 blur-3xl" />

          <div className="relative flex flex-col items-start gap-7 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <p className="text-sm font-medium text-white/70">{greeting()}, {name}</p>
              <h1 className="mt-2 max-w-md text-[1.75rem] font-extrabold leading-tight tracking-tight sm:text-[2rem]">
                You&apos;re {Math.round(learner.overallProgress * 100)}% closer to your target IELTS score.
              </h1>
              <Link
                href="/practice"
                className="mt-6 inline-flex h-12 items-center gap-2 rounded-xl bg-white px-5 text-sm font-semibold text-[var(--brand)] transition-transform duration-200 hover:-translate-y-0.5"
              >
                Continue practising
                <ArrowRight className="h-4 w-4" />
              </Link>
            </div>

            <Ring value={learner.overallProgress}>
              <span className="text-3xl font-extrabold">
                {Math.round(learner.overallProgress * 100)}%
              </span>
              <span className="text-xs text-white/70">to Band {learner.targetBand}</span>
            </Ring>
          </div>
        </section>

        {/* skill progress */}
        <section className="animate-fade-up rounded-3xl border border-[var(--border)] bg-white p-6 shadow-sm shadow-slate-200/40 [animation-delay:120ms]">
          <h2 className="text-base font-semibold text-[var(--text-primary)]">Skill progress</h2>
          <div className="mt-5 space-y-5">
            {SKILLS.map((s) => (
              <SkillRow key={s} skill={s} />
            ))}
          </div>
        </section>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        {/* recent activity */}
        <section className="animate-fade-up rounded-3xl border border-[var(--border)] bg-white p-6 shadow-sm shadow-slate-200/40 [animation-delay:160ms] lg:col-span-2">
          <div className="flex items-center justify-between">
            <h2 className="text-base font-semibold text-[var(--text-primary)]">Recent activity</h2>
            <Link href="/analytics" className="text-sm font-semibold text-[var(--brand)] hover:underline">
              View all
            </Link>
          </div>
          <div className="mt-4 divide-y divide-[var(--border)]">
            {recentActivity.map((a, i) => {
              const m = skillMeta[a.skill];
              const t = toneClasses[m.tone];
              const Icon = skillIcons[a.skill];
              return (
                <div key={i} className="flex items-center gap-4 py-3.5">
                  <span className={`flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-xl ${t.soft}`}>
                    <Icon className="h-5 w-5" />
                  </span>
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-semibold text-[var(--text-primary)]">{a.title}</p>
                    <p className="truncate text-xs text-[var(--text-secondary)]">{a.detail}</p>
                  </div>
                  {a.band != null && (
                    <span className="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-bold text-[var(--text-primary)]">
                      {a.band.toFixed(1)}
                    </span>
                  )}
                  <span className="hidden w-20 text-right text-xs text-[var(--text-secondary)] sm:block">
                    {a.when}
                  </span>
                </div>
              );
            })}
          </div>
        </section>

        {/* leaderboard — secondary */}
        <section className="animate-fade-up rounded-3xl border border-[var(--border)] bg-white p-6 shadow-sm shadow-slate-200/40 [animation-delay:200ms]">
          <div className="flex items-center gap-2">
            <Trophy className="h-4 w-4 text-amber-500" />
            <h2 className="text-base font-semibold text-[var(--text-primary)]">Leaderboard</h2>
          </div>
          <p className="mt-1 text-xs text-[var(--text-secondary)]">Highest streaks this week</p>
          <div className="mt-4 space-y-2.5">
            {leaderboard.highestStreaks.map((r, i) => {
              const you = r.name === "You";
              return (
                <div
                  key={r.name}
                  className={`flex items-center gap-3 rounded-xl px-3 py-2.5 ${
                    you ? "bg-[var(--brand)]/[0.06] ring-1 ring-[var(--brand)]/20" : ""
                  }`}
                >
                  <span className="w-5 text-sm font-bold text-[var(--text-secondary)]">{i + 1}</span>
                  <span className="flex h-8 w-8 items-center justify-center rounded-full bg-slate-100 text-xs font-semibold text-[var(--text-primary)]">
                    {r.name[0]}
                  </span>
                  <span className={`flex-1 text-sm font-medium ${you ? "text-[var(--brand)]" : "text-[var(--text-primary)]"}`}>
                    {r.name}
                  </span>
                  <span className="inline-flex items-center gap-1 text-sm font-semibold text-amber-500">
                    <Flame className="h-3.5 w-3.5" />
                    {r.days}
                  </span>
                </div>
              );
            })}
          </div>
          <p className="mt-4 text-center text-xs text-[var(--text-secondary)]">
            Weekly learners · Top improvements update every Monday
          </p>
        </section>
      </div>

      {/* weekly goal strip */}
      <section className="animate-fade-up rounded-3xl border border-[var(--border)] bg-white p-6 shadow-sm shadow-slate-200/40 [animation-delay:240ms]">
        <div className="flex items-center justify-between text-sm">
          <span className="font-semibold text-[var(--text-primary)]">This week&apos;s goal</span>
          <span className="text-[var(--text-secondary)]">
            {learner.weeklyDoneHours}h / {learner.weeklyGoalHours}h
          </span>
        </div>
        <ProgressBar
          value={learner.weeklyDoneHours / learner.weeklyGoalHours}
          className="mt-3 h-2.5"
        />
      </section>
    </div>
  );
}
