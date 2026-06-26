"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Plus } from "lucide-react";
import { fadeUp, stagger, viewport } from "@/shared/lib/motion";

const FAQS = [
  {
    q: "Is Testora free to start?",
    a: "Yes. You can create an account and take practice tests for free. No credit card required to get started.",
  },
  {
    q: "Which IELTS skills are covered?",
    a: "The launch focus is Academic Reading and AI-supported Writing. Reading is auto-scored with answer explanations; Writing receives criterion-by-criterion AI feedback.",
  },
  {
    q: "How accurate is the AI band score?",
    a: "Our AI is prompted with the official IELTS band descriptors and gives criterion-by-criterion feedback. It is a strong practice guide, though your official result is always determined by a certified examiner.",
  },
  {
    q: "Can I track my progress over time?",
    a: "Yes. Attempts are saved to your profile, and analytics are generated from your real graded work.",
  },
  {
    q: "Do the tests follow the real exam format?",
    a: "Yes. The Reading tests follow the Academic Reading structure: three passages, 40 questions and a live countdown timer.",
  },
];

function Item({ q, a }: { q: string; a: string }) {
  const [open, setOpen] = useState(false);
  return (
    <motion.div
      variants={fadeUp}
      className="overflow-hidden rounded-2xl border border-slate-100 bg-white shadow-sm"
    >
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center justify-between gap-4 px-6 py-5 text-left"
      >
        <span className="text-base font-semibold text-slate-900">{q}</span>
        <motion.span
          animate={{ rotate: open ? 45 : 0 }}
          transition={{ duration: 0.25 }}
          className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-full bg-blue-50 text-blue-600"
        >
          <Plus className="h-4 w-4" />
        </motion.span>
      </button>
      <AnimatePresence initial={false}>
        {open && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.3, ease: "easeInOut" }}
          >
            <p className="px-6 pb-5 text-sm leading-relaxed text-slate-600">{a}</p>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}

export default function FAQ() {
  return (
    <section id="faq" className="mx-auto max-w-3xl scroll-mt-24 px-5 py-20 lg:py-28">
      <motion.div
        initial="hidden"
        whileInView="show"
        viewport={viewport}
        variants={fadeUp}
        className="text-center"
      >
        <span className="text-sm font-semibold uppercase tracking-wider text-blue-600">FAQ</span>
        <h2 className="mt-3 text-4xl font-extrabold tracking-tight text-slate-900 sm:text-5xl">
          Frequently asked questions
        </h2>
        <p className="mt-4 text-lg text-slate-600">
          Everything you need to know before you start practising.
        </p>
      </motion.div>

      <motion.div
        initial="hidden"
        whileInView="show"
        viewport={viewport}
        variants={stagger}
        className="mt-12 space-y-3"
      >
        {FAQS.map((f) => (
          <Item key={f.q} {...f} />
        ))}
      </motion.div>
    </section>
  );
}
