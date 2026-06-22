"use client";

import { type ReactNode } from "react";
import Link from "next/link";
import { Headphones, BookOpen, PenLine, Mic, TrendingUp } from "lucide-react";
import GuestNavbar from "./GuestNavbar";

const SKILLS = [
  { label: "Listening", icon: Headphones },
  { label: "Reading", icon: BookOpen },
  { label: "Writing", icon: PenLine },
  { label: "Speaking", icon: Mic },
];

export default function AuthShell({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-screen bg-[var(--background)]">
      <GuestNavbar />

      <div className="mx-auto grid max-w-6xl gap-10 px-6 pb-10 pt-8 sm:px-8 lg:min-h-[calc(100vh-76px)] lg:grid-cols-[1.35fr_1fr] lg:items-stretch lg:gap-12 lg:pb-12">
        {/* Left: brand panel */}
        <aside className="relative hidden overflow-hidden rounded-[28px] bg-[var(--brand)] p-12 text-white shadow-[0_20px_60px_-20px_rgba(37,99,235,0.45)] lg:flex lg:flex-col lg:justify-between xl:p-14">
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

          {/* marketing copy */}
          <div className="relative">
            <h2 className="max-w-md text-[2.75rem] font-extrabold leading-[1.08] tracking-tight">
              Practice with purpose, <span className="text-white/60">score higher.</span>
            </h2>
            <p className="mt-5 max-w-md text-[1.0625rem] leading-relaxed text-white/75">
              Real IELTS practice with instant feedback and measurable progress.
            </p>

            <div className="mt-7 flex flex-wrap gap-2.5">
              {SKILLS.map((s) => (
                <span
                  key={s.label}
                  className="inline-flex items-center gap-1.5 rounded-full bg-white/12 px-3.5 py-1.5 text-sm font-medium ring-1 ring-white/15 backdrop-blur"
                >
                  <s.icon className="h-4 w-4" />
                  {s.label}
                </span>
              ))}
            </div>
          </div>

          {/* progress mockup — makes the panel read as a real SaaS marketing block */}
          <div className="relative rounded-2xl border border-white/15 bg-white/10 p-5 backdrop-blur-sm">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-white/60">Your target band</p>
                <p className="mt-0.5 text-3xl font-extrabold tracking-tight">7.5</p>
              </div>
              <span className="inline-flex items-center gap-1.5 rounded-full bg-white/15 px-3 py-1.5 text-xs font-semibold">
                <TrendingUp className="h-3.5 w-3.5" />
                +0.5 this month
              </span>
            </div>
            <div className="mt-4 h-2 overflow-hidden rounded-full bg-white/15">
              <div className="h-full w-[82%] rounded-full bg-white" />
            </div>
            <p className="mt-2 text-xs text-white/55">82% toward your goal</p>
          </div>
        </aside>

        {/* Right: form column — centered, not floating alone */}
        <main className="flex w-full items-center justify-center">
          <div className="w-full max-w-[460px] py-6">{children}</div>
        </main>
      </div>
    </div>
  );
}
