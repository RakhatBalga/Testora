"use client";

import { useState, type ReactNode } from "react";
import Link from "next/link";
import { Headphones, BookOpen, PenLine, Mic } from "lucide-react";
import GuestNavbar from "./GuestNavbar";

const LANGS = ["Eng", "Рус", "Қаз"];

const SKILLS = [
  { label: "Listening", icon: Headphones },
  { label: "Reading", icon: BookOpen },
  { label: "Writing", icon: PenLine },
  { label: "Speaking", icon: Mic },
];

export default function AuthShell({ children }: { children: ReactNode }) {
  const [lang, setLang] = useState("Eng");

  return (
    <div className="min-h-screen bg-[#F7F8FA]">
      <GuestNavbar />

      <div className="mx-auto grid max-w-6xl gap-8 px-5 pb-10 pt-[94px] sm:px-8 lg:min-h-screen lg:grid-cols-2 lg:items-center lg:gap-12 lg:pb-12">
        {/* Left: brand panel */}
        <aside className="relative hidden overflow-hidden rounded-[24px] bg-[var(--brand)] p-10 text-white shadow-xl shadow-[var(--brand)]/20 lg:flex lg:h-[calc(100vh-118px)] lg:flex-col lg:justify-between lg:p-14">
          {/* decorative elements */}
          <div
            className="pointer-events-none absolute inset-0 opacity-[0.14]"
            style={{
              backgroundImage:
                "radial-gradient(circle at 1px 1px, white 1px, transparent 0)",
              backgroundSize: "22px 22px",
            }}
          />
          <div className="pointer-events-none absolute -right-16 -top-16 h-64 w-64 rounded-full bg-white/10 blur-2xl" />
          <div className="pointer-events-none absolute -bottom-20 -left-10 h-72 w-72 rounded-full bg-black/10 blur-3xl" />

          {/* logo */}
          <Link href="/" className="relative flex items-center gap-3">
            <span className="flex h-11 w-11 items-center justify-center rounded-2xl bg-white/15 text-lg font-bold backdrop-blur">
              T
            </span>
            <span className="text-2xl font-bold tracking-tight">Testora</span>
          </Link>

          {/* marketing copy */}
          <div className="relative">
            <h2 className="text-[2.75rem] font-extrabold leading-[1.05] tracking-tight">
              Practice with
              <br />
              purpose,
              <br />
              <span className="text-white/55">score higher</span>
            </h2>
            <p className="mt-6 max-w-sm text-base leading-relaxed text-white/75">
              Realistic IELTS practice across every skill, with instant feedback and progress you
              can measure.
            </p>

            <div className="mt-8 flex flex-wrap gap-2.5">
              {SKILLS.map((s) => (
                <span
                  key={s.label}
                  className="inline-flex items-center gap-1.5 rounded-full bg-white/12 px-3.5 py-1.5 text-sm font-medium backdrop-blur"
                >
                  <s.icon className="h-4 w-4" />
                  {s.label}
                </span>
              ))}
            </div>
          </div>
        </aside>

        {/* Right: form column */}
        <main className="flex w-full flex-col">
          {/* language switcher */}
          <div className="mb-8 flex justify-center lg:justify-end">
            <div className="inline-flex rounded-full border border-slate-200 bg-white p-1">
              {LANGS.map((l) => (
                <button
                  key={l}
                  type="button"
                  onClick={() => setLang(l)}
                  className={`rounded-full px-4 py-1.5 text-sm font-medium transition-colors ${
                    lang === l
                      ? "bg-slate-900 text-white"
                      : "text-slate-500 hover:text-slate-900"
                  }`}
                >
                  {l}
                </button>
              ))}
            </div>
          </div>

          <div className="mx-auto w-full max-w-md">{children}</div>
        </main>
      </div>
    </div>
  );
}
