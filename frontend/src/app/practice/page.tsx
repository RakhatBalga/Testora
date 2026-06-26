"use client";

import Link from "next/link";
import { ArrowRight } from "lucide-react";
import { useRequireAuth } from "@/shared/auth";
import { SKILLS, skillMeta, toneClasses } from "@/entities/dashboard";
import { PageHeader, skillIcons } from "@/shared/ui/dashboard";

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
              <span className={`flex h-12 w-12 items-center justify-center rounded-2xl ${t.soft}`}>
                <Icon className="h-6 w-6" />
              </span>

              <h2 className="mt-4 text-xl font-bold text-[var(--text-primary)]">{m.label}</h2>
              <p className="mt-1 text-sm text-[var(--text-secondary)]">{m.blurb}</p>

              <span className="mt-5 inline-flex items-center gap-1.5 text-sm font-semibold text-[var(--brand)]">
                Start practicing
                <ArrowRight className="h-4 w-4 transition-transform duration-300 group-hover:translate-x-1" />
              </span>
            </Link>
          );
        })}
      </div>
    </div>
  );
}
