"use client";

import { type ReactNode } from "react";
import Link from "next/link";
import { Check, TrendingUp } from "lucide-react";
import GuestNavbar from "./GuestNavbar";

export type AuthPanel = {
  eyebrow?: string;
  title: ReactNode;
  subtitle: string;
  features?: string[];
};

const DEFAULT_FEATURES = [
  "Personalized study plan",
  "AI-powered feedback",
  "Full IELTS simulation",
  "Progress tracking",
];

export default function AuthShell({
  children,
  panel,
  progress,
  stepKey,
}: {
  children: ReactNode;
  panel: AuthPanel;
  progress?: { step: number; total: number };
  stepKey?: string | number;
}) {
  const features = panel.features ?? DEFAULT_FEATURES;
  const pct = progress ? Math.round((progress.step / progress.total) * 100) : 0;

  return (
    <div className="min-h-screen bg-[var(--background)]">
      <GuestNavbar />

      <div className="mx-auto grid max-w-6xl gap-10 px-6 pb-10 pt-8 sm:px-8 lg:min-h-[calc(100vh-76px)] lg:grid-cols-[1.22fr_1fr] lg:items-stretch lg:gap-12 lg:pb-12">
        {/* Left: brand panel — content changes per step */}
        <aside className="relative hidden overflow-hidden rounded-[28px] bg-[var(--brand)] p-12 text-white shadow-[0_20px_60px_-20px_rgba(37,99,235,0.45)] lg:flex lg:flex-col lg:justify-between lg:gap-12 xl:p-14">
          {/* academic dot grid */}
          <div
            className="pointer-events-none absolute inset-0 opacity-[0.12]"
            style={{
              backgroundImage:
                "radial-gradient(circle at 1px 1px, white 1px, transparent 0)",
              backgroundSize: "24px 24px",
            }}
          />
          {/* soft same-hue highlights (no rainbow gradients) */}
          <div className="pointer-events-none absolute -right-20 -top-24 h-72 w-72 rounded-full bg-[var(--brand-light)]/40 blur-3xl" />
          <div className="pointer-events-none absolute -bottom-24 -left-16 h-80 w-80 rounded-full bg-[var(--brand-dark)]/50 blur-3xl" />

          {/* logo */}
          <Link href="/" className="relative flex items-center gap-3">
            <span className="flex h-11 w-11 items-center justify-center rounded-2xl bg-white/15 text-lg font-bold backdrop-blur">
              T
            </span>
            <span className="text-2xl font-bold tracking-tight">Testora</span>
          </Link>

          {/* marketing copy — re-animates when the step changes */}
          <div key={stepKey} className="relative animate-fade-up">
            {panel.eyebrow && (
              <p className="mb-3 text-sm font-semibold uppercase tracking-wider text-white/60">
                {panel.eyebrow}
              </p>
            )}
            <h2 className="max-w-md text-[2.5rem] font-extrabold leading-[1.1] tracking-tight">
              {panel.title}
            </h2>
            <p className="mt-4 max-w-md text-[1.0625rem] leading-relaxed text-white/75">
              {panel.subtitle}
            </p>

            <ul className="mt-8 space-y-3.5">
              {features.map((f) => (
                <li key={f} className="flex items-center gap-3 text-[0.975rem] font-medium">
                  <span className="flex h-6 w-6 flex-shrink-0 items-center justify-center rounded-full bg-white/15 ring-1 ring-white/20">
                    <Check className="h-3.5 w-3.5" strokeWidth={3} />
                  </span>
                  {f}
                </li>
              ))}
            </ul>
          </div>

          {/* progress preview */}
          <div className="relative rounded-2xl border border-white/15 bg-white/10 p-6 backdrop-blur-sm">
            <div className="flex items-start justify-between gap-4">
              <div>
                <p className="text-xs font-medium uppercase tracking-wide text-white/55">
                  Your target band
                </p>
                <p className="mt-1.5 text-4xl font-extrabold leading-none tracking-tight">7.5</p>
              </div>
              <span className="inline-flex flex-shrink-0 items-center gap-1.5 rounded-full bg-white/15 px-3 py-1.5 text-xs font-semibold">
                <TrendingUp className="h-3.5 w-3.5" />
                +0.5 this month
              </span>
            </div>
            <div className="mt-5 h-2 overflow-hidden rounded-full bg-white/15">
              <div className="h-full w-[82%] rounded-full bg-white" />
            </div>
            <p className="mt-2.5 text-xs text-white/55">82% toward your goal</p>
          </div>
        </aside>

        {/* Right: form column */}
        <main className="flex w-full items-center justify-center">
          <div className="w-full max-w-[560px] py-6">
            {progress && (
              <div className="mb-9">
                <div className="mb-2 flex items-center justify-between text-sm font-medium">
                  <span className="text-[var(--text-primary)]">
                    Step {progress.step} of {progress.total}
                  </span>
                  <span className="text-[var(--text-secondary)]">{pct}%</span>
                </div>
                <div className="h-2 overflow-hidden rounded-full bg-[var(--border)]">
                  <div
                    className="h-full rounded-full bg-[var(--brand)] transition-[width] duration-500 ease-out"
                    style={{ width: `${pct}%` }}
                  />
                </div>
              </div>
            )}
            {children}
          </div>
        </main>
      </div>
    </div>
  );
}
