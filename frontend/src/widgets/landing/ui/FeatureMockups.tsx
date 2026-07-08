"use client";

import { motion } from "framer-motion";
import { MousePointer2, Flame, TrendingUp, Sparkles } from "lucide-react";
import { fadeUp, viewport, EASE } from "@/shared/lib/motion";

/** Caption line that sits above each mockup card, alims-style. */
function Caption({ children, align = "left" }: { children: string; align?: "left" | "right" }) {
  return (
    <motion.p
      variants={fadeUp}
      className={`mb-4 text-lg font-semibold text-slate-800 sm:text-xl ${
        align === "right" ? "text-right" : "text-left"
      }`}
    >
      {children}
    </motion.p>
  );
}

function CardShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="overflow-hidden rounded-[28px] border border-slate-200/70 bg-white shadow-[0_18px_50px_-24px_rgba(15,23,42,0.18)]">
      {children}
    </div>
  );
}

/* ------------------------- Mistake Notebook mockup ------------------------ */

const MISTAKES = [
  { label: "Comma splice", cat: "Grammar", sev: "high" },
  { label: "Overused 'very'", cat: "Lexical Resource", sev: "mid" },
  { label: "No clear thesis", cat: "Task Response", sev: "high" },
  { label: "Weak paragraph link", cat: "Coherence", sev: "mid" },
];

function MistakeNotebook() {
  return (
    <CardShell>
      <div className="border-b border-slate-100 bg-slate-50/70 px-6 py-4">
        <p className="font-mono text-sm font-semibold tracking-tight text-[var(--brand)]">
          Mistake Notebook
        </p>
      </div>
      <div className="relative space-y-2.5 p-6">
        {MISTAKES.map((m, i) => (
          <motion.div
            key={m.label}
            initial={{ opacity: 0, x: -18 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={viewport}
            transition={{ duration: 0.45, ease: EASE, delay: 0.15 + i * 0.12 }}
            className={`flex items-center justify-between rounded-xl border px-4 py-3 ${
              i === 2 ? "border-blue-200 bg-blue-50/60" : "border-slate-100 bg-white"
            }`}
          >
            <div className="flex items-center gap-3">
              <span
                className={`h-2 w-2 flex-shrink-0 rounded-full ${
                  m.sev === "high" ? "bg-red-400" : "bg-amber-400"
                }`}
              />
              <span className="text-sm font-medium text-slate-800">{m.label}</span>
            </div>
            <span className="rounded-full bg-slate-100 px-2.5 py-1 text-[11px] font-semibold text-slate-500">
              {m.cat}
            </span>
          </motion.div>
        ))}

        {/* animated cursor + tooltip, like a ghost user reviewing a mistake */}
        <motion.div
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1, x: [40, 0], y: [30, 0] }}
          viewport={viewport}
          transition={{ duration: 0.9, ease: EASE, delay: 0.9 }}
          className="pointer-events-none absolute right-10 top-[52%]"
        >
          <MousePointer2 className="h-5 w-5 fill-[var(--brand)] text-[var(--brand)]" />
          <motion.div
            initial={{ opacity: 0, scale: 0.9 }}
            whileInView={{ opacity: 1, scale: 1 }}
            viewport={viewport}
            transition={{ duration: 0.4, ease: EASE, delay: 1.5 }}
            className="ml-4 mt-1 w-max rounded-xl bg-slate-900 px-3.5 py-2 shadow-lg"
          >
            <p className="text-[11px] font-semibold text-white">Blocking Band 7.0</p>
            <p className="text-[10px] text-slate-300">Fix thesis clarity first</p>
          </motion.div>
        </motion.div>
      </div>
    </CardShell>
  );
}

/* --------------------------- Streak heatmap card -------------------------- */

const WEEKS = 10;
const DAYS = 7;
// Deterministic pseudo-random intensity so SSR/CSR render identically.
function intensity(w: number, d: number) {
  const v = Math.abs(Math.sin(w * 3.7 + d * 1.3)) * (w / WEEKS);
  if (v > 0.55) return 3;
  if (v > 0.38) return 2;
  if (v > 0.22) return 1;
  return 0;
}
const CELL_COLORS = ["bg-slate-100", "bg-blue-200", "bg-blue-400", "bg-[var(--brand)]"];

function StreakHeatmap() {
  return (
    <CardShell>
      <div className="border-b border-slate-100 bg-slate-50/70 px-6 py-4">
        <p className="font-mono text-sm font-semibold tracking-tight text-[var(--brand)]">
          Activity — last 10 weeks
        </p>
      </div>
      <div className="flex items-center gap-6 p-6">
        <div className="grid flex-1 grid-cols-10 gap-1.5">
          {Array.from({ length: WEEKS * DAYS }).map((_, i) => {
            const w = i % WEEKS;
            const d = Math.floor(i / WEEKS);
            return (
              <motion.div
                key={i}
                initial={{ opacity: 0, scale: 0.5 }}
                whileInView={{ opacity: 1, scale: 1 }}
                viewport={viewport}
                transition={{ duration: 0.3, ease: EASE, delay: 0.2 + w * 0.06 + d * 0.015 }}
                className={`aspect-square rounded-[4px] ${CELL_COLORS[intensity(w, d)]}`}
              />
            );
          })}
        </div>
        <div className="hidden flex-shrink-0 space-y-4 sm:block">
          {[
            { n: "12", label: "day streak", icon: Flame },
            { n: "38", label: "sessions", icon: Sparkles },
            { n: "+1.0", label: "band moved", icon: TrendingUp },
          ].map((s, i) => (
            <motion.div
              key={s.label}
              initial={{ opacity: 0, y: 14 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={viewport}
              transition={{ duration: 0.45, ease: EASE, delay: 0.5 + i * 0.15 }}
              className="flex items-center gap-2.5"
            >
              <s.icon className="h-4 w-4 text-[var(--brand)]" />
              <div>
                <p className="text-xl font-extrabold leading-none text-slate-900">{s.n}</p>
                <p className="mt-0.5 font-mono text-[11px] text-slate-500">{s.label}</p>
              </div>
            </motion.div>
          ))}
        </div>
      </div>
    </CardShell>
  );
}

/* ------------------------- Writing feedback mockup ------------------------ */

const CRITERIA = [
  { name: "Task Response", band: 6.5, pct: 72 },
  { name: "Coherence & Cohesion", band: 7.0, pct: 78 },
  { name: "Lexical Resource", band: 6.0, pct: 67 },
  { name: "Grammatical Range", band: 6.5, pct: 72 },
];

function WritingFeedback() {
  return (
    <CardShell>
      <div className="flex items-center justify-between border-b border-slate-100 bg-slate-50/70 px-6 py-4">
        <p className="font-mono text-sm font-semibold tracking-tight text-[var(--brand)]">
          Writing — Task 2 review
        </p>
        <motion.span
          initial={{ scale: 0, rotate: -12 }}
          whileInView={{ scale: 1, rotate: 0 }}
          viewport={viewport}
          transition={{ duration: 0.5, ease: EASE, delay: 0.8 }}
          className="rounded-full bg-[var(--brand)] px-3 py-1 text-sm font-extrabold text-white"
        >
          6.5
        </motion.span>
      </div>
      <div className="space-y-4 p-6">
        {CRITERIA.map((c, i) => (
          <div key={c.name}>
            <div className="mb-1.5 flex items-center justify-between text-sm">
              <span className="font-medium text-slate-700">{c.name}</span>
              <span className="font-bold text-slate-900">{c.band.toFixed(1)}</span>
            </div>
            <div className="h-2 overflow-hidden rounded-full bg-slate-100">
              <motion.div
                initial={{ width: 0 }}
                whileInView={{ width: `${c.pct}%` }}
                viewport={viewport}
                transition={{ duration: 0.9, ease: EASE, delay: 0.25 + i * 0.15 }}
                className="h-full rounded-full bg-[var(--brand)]"
              />
            </div>
          </div>
        ))}
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={viewport}
          transition={{ duration: 0.5, ease: EASE, delay: 1 }}
          className="rounded-xl bg-blue-50/70 px-4 py-3"
        >
          <p className="text-xs font-semibold uppercase tracking-wide text-[var(--brand)]">
            Coach note
          </p>
          <p className="mt-1 text-sm text-slate-600">
            Lexical Resource is your blocker — practise paraphrasing today.
          </p>
        </motion.div>
      </div>
    </CardShell>
  );
}

/* ----------------------- Band trajectory chart card ----------------------- */

function BandTrajectory() {
  const bars = [48, 55, 52, 64, 70, 66, 78, 88];
  return (
    <CardShell>
      <div className="border-b border-slate-100 bg-slate-50/70 px-6 py-4">
        <p className="font-mono text-sm font-semibold tracking-tight text-[var(--brand)]">
          Band trajectory
        </p>
      </div>
      <div className="p-6">
        <div className="flex h-44 items-end gap-2.5">
          {bars.map((h, i) => (
            <motion.div
              key={i}
              initial={{ height: 0 }}
              whileInView={{ height: `${h}%` }}
              viewport={viewport}
              transition={{ duration: 0.7, ease: EASE, delay: 0.15 + i * 0.09 }}
              className={`flex-1 rounded-t-lg ${
                i === bars.length - 1 ? "bg-[var(--brand)]" : "bg-blue-200"
              }`}
            />
          ))}
        </div>
        <div className="mt-3 flex items-center justify-between">
          <p className="font-mono text-xs text-slate-400">8 weeks of graded work</p>
          <motion.p
            initial={{ opacity: 0, x: 12 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={viewport}
            transition={{ duration: 0.5, ease: EASE, delay: 1 }}
            className="text-sm font-bold text-emerald-600"
          >
            6.0 → 7.0
          </motion.p>
        </div>
      </div>
    </CardShell>
  );
}

/* --------------------------------- Section -------------------------------- */

export default function FeatureMockups() {
  return (
    <section id="features" className="scroll-mt-24 px-4 pt-4 sm:px-6">
      <div className="mx-auto max-w-[1400px] rounded-[32px] bg-slate-50/80 px-6 py-16 sm:px-10 sm:py-20">
        <motion.h2
          initial="hidden"
          whileInView="show"
          viewport={viewport}
          variants={fadeUp}
          className="text-center text-3xl font-extrabold tracking-tight text-slate-900 sm:text-5xl"
        >
          Our Platform Features
        </motion.h2>

        <motion.div
          initial="hidden"
          whileInView="show"
          viewport={viewport}
          variants={{ show: { transition: { staggerChildren: 0.15 } } }}
          className="mt-14 grid gap-x-8 gap-y-12 lg:grid-cols-2"
        >
          <motion.div variants={fadeUp}>
            <Caption>Every mistake, remembered for you</Caption>
            <MistakeNotebook />
          </motion.div>
          <motion.div variants={fadeUp}>
            <Caption align="right">Stay consistent. Improve every day</Caption>
            <StreakHeatmap />
          </motion.div>
          <motion.div variants={fadeUp}>
            <Caption>AI feedback on all four criteria</Caption>
            <WritingFeedback />
          </motion.div>
          <motion.div variants={fadeUp}>
            <Caption align="right">Watch your band actually move</Caption>
            <BandTrajectory />
          </motion.div>
        </motion.div>
      </div>
    </section>
  );
}
