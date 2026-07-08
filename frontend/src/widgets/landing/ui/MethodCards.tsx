"use client";

import { motion } from "framer-motion";
import { PenLine, SearchCheck, Crosshair, CalendarCheck, type LucideIcon } from "lucide-react";
import { fadeUp, stagger, viewport } from "@/shared/lib/motion";

type Step = {
  icon: LucideIcon;
  step: string;
  title: string;
  body: string;
};

const STEPS: Step[] = [
  {
    icon: PenLine,
    step: "01",
    title: "Submit real work",
    body: "Write a Task 2 essay or record a Speaking answer — the coach grades it against all four IELTS criteria.",
  },
  {
    icon: SearchCheck,
    step: "02",
    title: "Mistakes extracted",
    body: "Every error is saved to your Mistake Notebook with the snippet, the correction, and why it matters.",
  },
  {
    icon: Crosshair,
    step: "03",
    title: "Blocker named",
    body: "The engine finds the one criterion capping your band — so you stop practising blindly.",
  },
  {
    icon: CalendarCheck,
    step: "04",
    title: "Today's plan",
    body: "You get a short, concrete task list for today. Re-grade later and watch the band move.",
  },
];

export default function MethodCards() {
  return (
    <section className="relative overflow-hidden px-4 pt-4 sm:px-6">
      <div className="relative mx-auto max-w-[1400px] overflow-hidden rounded-[32px] bg-gradient-to-br from-[#2563eb] to-[#1d4ed8] px-6 py-16 sm:px-10 sm:py-20">
        {/* diagonal accents, echoing the section's forward motion */}
        <div aria-hidden className="pointer-events-none absolute inset-0">
          <div className="absolute -left-40 top-0 h-[200%] w-64 -rotate-[24deg] bg-white/[0.06]" />
          <div className="absolute -right-24 bottom-0 h-[200%] w-40 -rotate-[24deg] bg-white/[0.06]" />
        </div>

        <motion.div
          initial="hidden"
          whileInView="show"
          viewport={viewport}
          variants={fadeUp}
          className="relative mx-auto max-w-2xl text-center"
        >
          <h2 className="text-3xl font-extrabold tracking-tight text-white sm:text-5xl">
            The coach loop
          </h2>
          <p className="mt-4 text-lg text-white/75">
            Not another question bank — a loop that turns every attempt into
            a sharper plan.
          </p>
        </motion.div>

        <motion.div
          initial="hidden"
          whileInView="show"
          viewport={viewport}
          variants={stagger}
          className="relative mt-12 grid gap-5 sm:grid-cols-2 lg:grid-cols-4"
        >
          {STEPS.map((s) => (
            <motion.div
              key={s.step}
              variants={fadeUp}
              className="rounded-3xl border border-white/10 bg-white/[0.08] p-7 backdrop-blur-sm transition-colors duration-300 hover:bg-white/[0.14]"
            >
              <div className="flex items-center justify-between">
                <span className="flex h-11 w-11 items-center justify-center rounded-2xl bg-white/15 text-white">
                  <s.icon className="h-5 w-5" />
                </span>
                <span className="text-sm font-bold tracking-widest text-white/40">{s.step}</span>
              </div>
              <h3 className="mt-5 text-lg font-semibold text-white">{s.title}</h3>
              <p className="mt-2 text-sm leading-relaxed text-white/70">{s.body}</p>
            </motion.div>
          ))}
        </motion.div>
      </div>
    </section>
  );
}
