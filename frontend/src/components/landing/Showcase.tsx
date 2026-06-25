"use client";

import { motion } from "framer-motion";
import { CheckCircle2, BarChart3, TrendingUp } from "lucide-react";
import { fadeUp, stagger, viewport, EASE } from "./motion";

const POINTS = [
  { title: "Detailed analytics", body: "See exactly where you lose marks across every skill." },
  { title: "Progress tracking", body: "Band scores saved after every attempt, charted over time." },
  { title: "Full-length tests", body: "Reading and Listening tests with a realistic exam timer." },
  { title: "Writing & Speaking tasks", body: "Authentic prompts graded against IELTS descriptors." },
  { title: "Answer review", body: "Walk through every question with the correct answer." },
  { title: "AI Coach", body: "Streak tracking and a personalised daily plan keep your practice consistent." },
];

export default function Showcase() {
  return (
    <section id="showcase" className="relative scroll-mt-24 overflow-hidden bg-white py-20 lg:py-28">
      <div className="mx-auto grid max-w-6xl items-center gap-14 px-5 lg:grid-cols-2">
        {/* Left: mock interface */}
        <motion.div
          initial={{ opacity: 0, x: -40 }}
          whileInView={{ opacity: 1, x: 0 }}
          viewport={viewport}
          transition={{ duration: 0.6, ease: EASE }}
          className="relative order-2 lg:order-1"
        >
          <div className="absolute -inset-4 -z-10 rounded-[32px] bg-blue-50 blur-2xl" />
          <div className="rounded-3xl border border-slate-100 bg-white p-6 shadow-2xl shadow-slate-300/40">
            <div className="mb-5 flex items-center justify-between">
              <p className="font-semibold text-slate-900">Performance</p>
              <span className="rounded-full bg-emerald-50 px-2.5 py-1 text-xs font-semibold text-emerald-700">
                +1.5 this month
              </span>
            </div>

            {/* fake bar chart */}
            <div className="flex h-40 items-end gap-3">
              {[55, 70, 60, 82, 75, 92].map((h, i) => (
                <motion.div
                  key={i}
                  initial={{ height: 0 }}
                  whileInView={{ height: `${h}%` }}
                  viewport={viewport}
                  transition={{ duration: 0.7, ease: EASE, delay: i * 0.1 }}
                  className="flex-1 rounded-t-lg bg-gradient-to-t from-blue-600 to-blue-400"
                />
              ))}
            </div>
            <div className="mt-3 flex justify-between text-xs text-slate-400">
              {["Wk 1", "Wk 2", "Wk 3", "Wk 4", "Wk 5", "Wk 6"].map((w) => (
                <span key={w}>{w}</span>
              ))}
            </div>

            <div className="mt-6 grid grid-cols-2 gap-3">
              <div className="rounded-2xl bg-slate-50 p-4">
                <BarChart3 className="h-5 w-5 text-blue-500" />
                <p className="mt-2 text-2xl font-bold text-slate-900">128</p>
                <p className="text-xs text-slate-500">Tests completed</p>
              </div>
              <div className="rounded-2xl bg-slate-50 p-4">
                <TrendingUp className="h-5 w-5 text-blue-600" />
                <p className="mt-2 text-2xl font-bold text-slate-900">7.5</p>
                <p className="text-xs text-slate-500">Current band</p>
              </div>
            </div>
          </div>
        </motion.div>

        {/* Right: checklist */}
        <motion.div
          initial="hidden"
          whileInView="show"
          viewport={viewport}
          variants={stagger}
          className="order-1 lg:order-2"
        >
          <motion.span variants={fadeUp} className="text-sm font-semibold uppercase tracking-wider text-blue-600">
            The platform
          </motion.span>
          <motion.h2
            variants={fadeUp}
            className="mt-3 text-4xl font-extrabold tracking-tight text-slate-900 sm:text-5xl"
          >
            Everything in one clean dashboard
          </motion.h2>
          <motion.p variants={fadeUp} className="mt-4 text-lg text-slate-600">
            Practice, review and track — without juggling books, PDFs and spreadsheets.
          </motion.p>

          <motion.ul variants={stagger} className="mt-8 grid gap-4 sm:grid-cols-2">
            {POINTS.map((p) => (
              <motion.li key={p.title} variants={fadeUp} className="flex gap-3">
                <CheckCircle2 className="mt-0.5 h-5 w-5 flex-shrink-0 text-blue-600" />
                <div>
                  <p className="font-semibold text-slate-900">{p.title}</p>
                  <p className="text-sm text-slate-600">{p.body}</p>
                </div>
              </motion.li>
            ))}
          </motion.ul>
        </motion.div>
      </div>
    </section>
  );
}
