"use client";

import { motion } from "framer-motion";
import {
  BookOpen,
  Zap,
  Sparkles,
  TrendingUp,
  Layers,
  Brain,
  type LucideIcon,
} from "lucide-react";
import { fadeUp, stagger, viewport } from "./motion";

type Feature = {
  icon: LucideIcon;
  title: string;
  body: string;
  color: string;
};

const FEATURES: Feature[] = [
  {
    icon: BookOpen,
    title: "Original Reading Tests",
    body: "Ten full Academic Reading tests with 40 questions each and natural IELTS-style passages.",
    color: "from-blue-500 to-indigo-500",
  },
  {
    icon: Zap,
    title: "Instant Reading Scoring",
    body: "Submit a timed Reading attempt and review every answer with a clear explanation.",
    color: "from-indigo-500 to-violet-500",
  },
  {
    icon: Sparkles,
    title: "AI Writing Feedback",
    body: "Task 1 and Task 2 responses are graded with band estimates, strengths, weaknesses and next steps.",
    color: "from-violet-500 to-fuchsia-500",
  },
  {
    icon: TrendingUp,
    title: "Progress Tracking",
    body: "Every attempt is saved so your band trajectory and recurring weaknesses are based on real work.",
    color: "from-fuchsia-500 to-pink-500",
  },
  {
    icon: Layers,
    title: "Evidence-Based Review",
    body: "Reading answers carry paragraph and sentence evidence, ready for highlighted review mode.",
    color: "from-sky-500 to-blue-500",
  },
  {
    icon: Brain,
    title: "AI Coach",
    body: "After each session, see your band blockers, recurring mistake patterns, and a personalised improvement plan for today.",
    color: "from-amber-500 to-orange-500",
  },
];

export default function Features() {
  return (
    <section id="features" className="mx-auto max-w-6xl scroll-mt-24 px-5 py-20 lg:py-28">
      <motion.div
        initial="hidden"
        whileInView="show"
        viewport={viewport}
        variants={fadeUp}
        className="mx-auto max-w-2xl text-center"
      >
        <span className="text-sm font-semibold uppercase tracking-wider text-blue-600">
          Features
        </span>
        <h2 className="mt-3 text-4xl font-extrabold tracking-tight text-slate-900 sm:text-5xl">
          Why choose our platform
        </h2>
        <p className="mt-4 text-lg text-slate-600">
          Everything you need to prepare smarter, practice realistically, and reach your target
          band with evidence you can inspect.
        </p>
      </motion.div>

      <motion.div
        initial="hidden"
        whileInView="show"
        viewport={viewport}
        variants={stagger}
        className="mt-14 grid gap-6 sm:grid-cols-2 lg:grid-cols-3"
      >
        {FEATURES.map((f) => (
          <motion.div
            key={f.title}
            variants={fadeUp}
            className="group rounded-3xl border border-slate-100 bg-white p-7 shadow-sm transition-all duration-300 hover:-translate-y-1.5 hover:border-slate-200 hover:shadow-xl hover:shadow-slate-200/60"
          >
            <span
              className={`flex h-12 w-12 items-center justify-center rounded-2xl bg-gradient-to-br text-white shadow-md transition-transform duration-300 group-hover:scale-110 ${f.color}`}
            >
              <f.icon className="h-6 w-6" />
            </span>
            <h3 className="mt-5 text-lg font-semibold text-slate-900">{f.title}</h3>
            <p className="mt-2 text-sm leading-relaxed text-slate-600">{f.body}</p>
          </motion.div>
        ))}
      </motion.div>
    </section>
  );
}
