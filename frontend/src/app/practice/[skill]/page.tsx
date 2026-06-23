"use client";

import { use } from "react";
import Link from "next/link";
import { notFound } from "next/navigation";
import { ArrowLeft, ArrowRight, Play } from "lucide-react";
import { useRequireAuth } from "@/hooks/useRequireAuth";
import {
  SKILLS,
  type Skill,
  skillMeta,
  toneClasses,
  practiceSections,
  recentActivity,
} from "@/lib/dashboard";
import { ProgressBar, skillIcons } from "@/components/dashboard/widgets";

/** Where "Start" sends the learner for each skill's real practice flow. */
const startHref: Record<Skill, string> = {
  listening: "/tests/listening",
  reading: "/tests/reading",
  writing: "/writing",
  speaking: "/speaking",
};

export default function SkillPracticePage({
  params,
}: {
  params: Promise<{ skill: string }>;
}) {
  const { skill } = use(params);
  const { token, ready } = useRequireAuth();

  if (!SKILLS.includes(skill as Skill)) notFound();
  const s = skill as Skill;

  if (!ready || !token) return null;

  const m = skillMeta[s];
  const t = toneClasses[m.tone];
  const Icon = skillIcons[s];
  const groups = practiceSections[s];
  const history = recentActivity.filter((a) => a.skill === s);

  return (
    <div className="space-y-8">
      <Link
        href="/practice"
        className="inline-flex items-center gap-1.5 text-sm font-medium text-[var(--text-secondary)] hover:text-[var(--text-primary)]"
      >
        <ArrowLeft className="h-4 w-4" />
        Practice
      </Link>

      {/* header card */}
      <section className="animate-fade-up rounded-3xl border border-[var(--border)] bg-white p-7 shadow-sm shadow-slate-200/40">
        <div className="flex flex-wrap items-center justify-between gap-5">
          <div className="flex items-center gap-4">
            <span className={`flex h-14 w-14 items-center justify-center rounded-2xl ${t.soft}`}>
              <Icon className="h-7 w-7" />
            </span>
            <div>
              <h1 className="text-2xl font-bold tracking-tight text-[var(--text-primary)]">
                {m.label}
              </h1>
              <p className="mt-0.5 text-sm text-[var(--text-secondary)]">{m.blurb}</p>
            </div>
          </div>
          <Link
            href={startHref[s]}
            className="inline-flex h-12 items-center gap-2 rounded-xl bg-[var(--brand)] px-5 text-sm font-semibold text-white shadow-sm shadow-[var(--brand)]/30 transition-all duration-200 hover:-translate-y-0.5 hover:bg-[var(--brand-dark)]"
          >
            <Play className="h-4 w-4" />
            Start session
          </Link>
        </div>

        <div className="mt-6 grid gap-4 sm:grid-cols-3">
          <Metric label="Overall progress" value={`${Math.round(m.progress * 100)}%`} />
          <Metric label="Exercises" value={String(m.exercises)} />
          <Metric label="Average band" value={m.avgBand.toFixed(1)} />
        </div>
      </section>

      {/* sections */}
      {groups.map((group) => (
        <section key={group.group} className="animate-fade-up [animation-delay:80ms]">
          <h2 className="mb-4 text-base font-semibold text-[var(--text-primary)]">{group.group}</h2>
          <div className="grid gap-4">
            {group.items.map((item) => (
              <Link
                key={item.name}
                href={startHref[s]}
                className="group flex items-center gap-4 rounded-2xl border border-[var(--border)] bg-white p-5 shadow-sm shadow-slate-200/40 transition duration-200 hover:-translate-y-0.5 hover:shadow-md"
              >
                <div className="min-w-0 flex-1">
                  <div className="flex items-center justify-between">
                    <p className="font-semibold text-[var(--text-primary)]">{item.name}</p>
                    <span className="text-sm font-semibold text-[var(--text-secondary)]">
                      {Math.round(item.progress * 100)}%
                    </span>
                  </div>
                  <p className="mb-2 mt-0.5 text-xs text-[var(--text-secondary)]">
                    {item.count} exercises
                  </p>
                  <ProgressBar value={item.progress} barClass={t.bar} />
                </div>
                <ArrowRight className="h-5 w-5 flex-shrink-0 text-slate-300 transition-transform duration-300 group-hover:translate-x-1 group-hover:text-[var(--brand)]" />
              </Link>
            ))}
          </div>
        </section>
      ))}

      {/* recent sessions */}
      {history.length > 0 && (
        <section className="animate-fade-up rounded-3xl border border-[var(--border)] bg-white p-6 shadow-sm shadow-slate-200/40 [animation-delay:120ms]">
          <h2 className="text-base font-semibold text-[var(--text-primary)]">Recent {m.label.toLowerCase()} sessions</h2>
          <div className="mt-4 divide-y divide-[var(--border)]">
            {history.map((a, i) => (
              <div key={i} className="flex items-center justify-between py-3 text-sm">
                <span className="font-medium text-[var(--text-primary)]">{a.title}</span>
                <span className="flex items-center gap-3">
                  <span className="text-xs text-[var(--text-secondary)]">{a.when}</span>
                  {a.band != null && (
                    <span className="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-bold text-[var(--text-primary)]">
                      {a.band.toFixed(1)}
                    </span>
                  )}
                </span>
              </div>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-2xl bg-slate-50 p-4">
      <p className="text-xs font-medium text-[var(--text-secondary)]">{label}</p>
      <p className="mt-1 text-2xl font-extrabold tracking-tight text-[var(--text-primary)]">{value}</p>
    </div>
  );
}
