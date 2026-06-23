"use client";

import Link from "next/link";
import { ArrowRight } from "lucide-react";
import { useRequireAuth } from "@/hooks/useRequireAuth";
import { SKILLS, skillMeta, toneClasses } from "@/lib/dashboard";
import { PageHeader, ProgressBar, skillIcons } from "@/components/dashboard/widgets";

export default function PracticePage() {
  const { token, ready } = useRequireAuth();
  if (!ready || !token) return null;

  return (
    <div className="space-y-8">
      <PageHeader
        title="Practice"
        subtitle="Sharpen each IELTS skill with targeted exercises and instant feedback."
      />

      <div className="grid gap-5 sm:grid-cols-2">
        {SKILLS.map((s, i) => {
          const m = skillMeta[s];
          const t = toneClasses[m.tone];
          const Icon = skillIcons[s];
          return (
            <Link
              key={s}
              href={m.href}
              className="group animate-fade-up rounded-3xl border border-[var(--border)] bg-white p-6 shadow-sm shadow-slate-200/40 transition duration-300 hover:-translate-y-1 hover:shadow-lg"
              style={{ animationDelay: `${i * 80}ms` }}
            >
              <div className="flex items-start justify-between">
                <span className={`flex h-12 w-12 items-center justify-center rounded-2xl ${t.soft}`}>
                  <Icon className="h-6 w-6" />
                </span>
                <span className="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-semibold text-[var(--text-secondary)]">
                  avg band {m.avgBand.toFixed(1)}
                </span>
              </div>

              <h2 className="mt-4 text-xl font-bold text-[var(--text-primary)]">{m.label}</h2>
              <p className="mt-1 text-sm text-[var(--text-secondary)]">{m.blurb}</p>

              <div className="mt-5">
                <div className="mb-1.5 flex items-center justify-between text-sm">
                  <span className="text-[var(--text-secondary)]">{m.exercises} exercises</span>
                  <span className="font-semibold text-[var(--text-primary)]">
                    {Math.round(m.progress * 100)}%
                  </span>
                </div>
                <ProgressBar value={m.progress} barClass={t.bar} />
              </div>

              <span className="mt-5 inline-flex items-center gap-1.5 text-sm font-semibold text-[var(--brand)]">
                Continue
                <ArrowRight className="h-4 w-4 transition-transform duration-300 group-hover:translate-x-1" />
              </span>
            </Link>
          );
        })}
      </div>
    </div>
  );
}
