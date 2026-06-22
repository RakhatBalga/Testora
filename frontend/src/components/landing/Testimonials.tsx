"use client";

import { motion } from "framer-motion";
import { Star } from "lucide-react";
import { fadeUp, stagger, viewport } from "./motion";

type Review = {
  name: string;
  role: string;
  initials: string;
  color: string;
  band: string;
  quote: string;
};

const REVIEWS: Review[] = [
  {
    name: "Aizhan K.",
    role: "Band 6.0 → 7.5",
    initials: "AK",
    color: "from-blue-500 to-indigo-500",
    band: "7.5",
    quote:
      "The AI feedback on my essays was a game changer. I finally understood why I was stuck at 6 and fixed it in weeks.",
  },
  {
    name: "Daniyar M.",
    role: "Band 5.5 → 7.0",
    initials: "DM",
    color: "from-violet-500 to-fuchsia-500",
    band: "7.0",
    quote:
      "Speaking always scared me. Recording answers and getting instant scores made practice feel safe and consistent.",
  },
  {
    name: "Sofia R.",
    role: "Band 7.0 → 8.0",
    initials: "SR",
    color: "from-fuchsia-500 to-pink-500",
    band: "8.0",
    quote:
      "Realistic timed tests and clear analytics. I knew exactly what to drill before test day. Hit my target on the first try.",
  },
  {
    name: "Nurlan B.",
    role: "Band 6.5 → 7.5",
    initials: "NB",
    color: "from-sky-500 to-blue-500",
    band: "7.5",
    quote:
      "Everything in one place — no more scattered PDFs. The progress chart kept me motivated every single day.",
  },
];

export default function Testimonials() {
  return (
    <section id="testimonials" className="mx-auto max-w-6xl scroll-mt-24 px-5 py-20 lg:py-28">
      <motion.div
        initial="hidden"
        whileInView="show"
        viewport={viewport}
        variants={fadeUp}
        className="mx-auto max-w-2xl text-center"
      >
        <span className="text-sm font-semibold uppercase tracking-wider text-indigo-600">
          Reviews
        </span>
        <h2 className="mt-3 text-4xl font-extrabold tracking-tight text-slate-900 sm:text-5xl">
          Loved by learners worldwide
        </h2>
        <p className="mt-4 text-lg text-slate-600">
          Thousands have raised their band score with focused, measurable practice.
        </p>
      </motion.div>

      <motion.div
        initial="hidden"
        whileInView="show"
        viewport={viewport}
        variants={stagger}
        className="mt-14 grid gap-6 sm:grid-cols-2 lg:grid-cols-4"
      >
        {REVIEWS.map((r) => (
          <motion.figure
            key={r.name}
            variants={fadeUp}
            className="flex h-full flex-col rounded-3xl border border-slate-100 bg-white p-6 shadow-sm transition-all duration-300 hover:-translate-y-1.5 hover:shadow-xl hover:shadow-slate-200/60"
          >
            <div className="mb-3 flex gap-0.5 text-amber-400">
              {Array.from({ length: 5 }).map((_, i) => (
                <Star key={i} className="h-4 w-4 fill-current" />
              ))}
            </div>
            <blockquote className="flex-1 text-sm leading-relaxed text-slate-600">
              “{r.quote}”
            </blockquote>
            <figcaption className="mt-5 flex items-center gap-3">
              <span
                className={`flex h-10 w-10 items-center justify-center rounded-full bg-gradient-to-br text-sm font-semibold text-white ${r.color}`}
              >
                {r.initials}
              </span>
              <div>
                <p className="text-sm font-semibold text-slate-900">{r.name}</p>
                <p className="text-xs text-slate-500">{r.role}</p>
              </div>
            </figcaption>
          </motion.figure>
        ))}
      </motion.div>
    </section>
  );
}
