"use client";

import Link from "next/link";
import { motion } from "framer-motion";
import { ArrowRight, Sparkles, Headphones, BookOpen, PenLine, Mic } from "lucide-react";
import { fadeUp, EASE } from "./motion";

const SKILLS = [
  { label: "Listening", band: 7.5, pct: 83, icon: Headphones, color: "from-blue-500 to-blue-600" },
  { label: "Reading", band: 8.0, pct: 89, icon: BookOpen, color: "from-blue-600 to-blue-700" },
  { label: "Writing", band: 6.5, pct: 72, icon: PenLine, color: "from-blue-500 to-blue-700" },
  { label: "Speaking", band: 7.0, pct: 78, icon: Mic, color: "from-blue-400 to-blue-600" },
];

export default function Hero() {
  return (
    <section className="relative overflow-hidden">
      {/* Soft background glow */}
      <div className="pointer-events-none absolute inset-0 -z-10">
        <div className="absolute -left-32 -top-32 h-96 w-96 rounded-full bg-blue-300/25 blur-3xl" />
        <div className="absolute -right-24 top-20 h-96 w-96 rounded-full bg-blue-200/20 blur-3xl" />
      </div>

      <div className="mx-auto grid max-w-6xl items-center gap-12 px-5 py-20 lg:grid-cols-2 lg:py-28">
        {/* Left: copy */}
        <motion.div initial="hidden" animate="show" variants={{ show: { transition: { staggerChildren: 0.09 } } }}>
          <motion.div variants={fadeUp}>
            <span className="inline-flex items-center gap-2 rounded-full border border-blue-100 bg-blue-50 px-4 py-1.5 text-sm font-medium text-blue-700">
              <Sparkles className="h-4 w-4" />
              AI-powered IELTS preparation
            </span>
          </motion.div>

          <motion.h1
            variants={fadeUp}
            className="mt-6 text-5xl font-extrabold leading-[1.05] tracking-tight text-slate-900 sm:text-6xl"
          >
            Get the band score you{" "}
            <span className="bg-gradient-to-r from-blue-600 to-blue-500 bg-clip-text text-transparent">
              actually want
            </span>
          </motion.h1>

          <motion.p variants={fadeUp} className="mt-6 max-w-lg text-lg leading-relaxed text-slate-600">
            Practice realistic Reading, Listening, Writing and Speaking tasks, get scored
            instantly with AI feedback, and watch your progress climb — all in one place.
          </motion.p>

          <motion.div variants={fadeUp} className="mt-9 flex flex-wrap items-center gap-3">
            <Link
              href="/register"
              className="group inline-flex items-center gap-2 rounded-2xl bg-[var(--brand)] px-7 py-4 text-base font-semibold text-white shadow-lg shadow-blue-500/25 transition-all duration-300 hover:bg-[var(--brand-dark)] hover:shadow-xl hover:shadow-blue-500/35"
            >
              Start Learning
              <ArrowRight className="h-5 w-5 transition-transform duration-300 group-hover:translate-x-1" />
            </Link>
            <Link
              href="/login"
              className="inline-flex items-center gap-2 rounded-2xl border border-slate-200 bg-white px-7 py-4 text-base font-semibold text-slate-700 shadow-sm transition-all duration-300 hover:border-slate-300 hover:shadow-md"
            >
              Log in
            </Link>
          </motion.div>

          <motion.div variants={fadeUp} className="mt-8 flex items-center gap-6 text-sm text-slate-500">
            <div>
              <span className="text-lg font-bold text-slate-900">12k+</span> learners
            </div>
            <div className="h-4 w-px bg-slate-200" />
            <div>
              <span className="text-lg font-bold text-slate-900">+1.2</span> avg band gain
            </div>
            <div className="h-4 w-px bg-slate-200" />
            <div>
              <span className="text-lg font-bold text-slate-900">4.9★</span> rating
            </div>
          </motion.div>
        </motion.div>

        {/* Right: animated dashboard mockup */}
        <motion.div
          initial={{ opacity: 0, y: 40, scale: 0.96 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          transition={{ duration: 0.7, ease: EASE, delay: 0.1 }}
          className="relative"
        >
          {/* floating badge top — only visible in 2-col layout */}
          <motion.div
            animate={{ y: [0, -10, 0] }}
            transition={{ duration: 4, repeat: Infinity, ease: "easeInOut" }}
            className="absolute -left-5 -top-6 z-10 hidden rounded-2xl border border-slate-100 bg-white px-4 py-3 shadow-xl lg:block"
          >
            <p className="text-xs text-slate-500">Overall band</p>
            <p className="text-2xl font-extrabold text-[var(--brand)]">
              7.5
            </p>
          </motion.div>

          {/* floating badge bottom — only visible in 2-col layout */}
          <motion.div
            animate={{ y: [0, 10, 0] }}
            transition={{ duration: 4.5, repeat: Infinity, ease: "easeInOut", delay: 0.5 }}
            className="absolute -right-3 bottom-10 z-10 hidden items-center gap-2 rounded-2xl border border-slate-100 bg-white px-4 py-3 shadow-xl lg:flex"
          >
            <span className="flex h-8 w-8 items-center justify-center rounded-full bg-emerald-50 text-emerald-600">
              <Sparkles className="h-4 w-4" />
            </span>
            <div>
              <p className="text-xs text-slate-500">AI feedback</p>
              <p className="text-sm font-semibold text-slate-900">Ready in seconds</p>
            </div>
          </motion.div>

          {/* main card */}
          <div className="rounded-[28px] border border-slate-100 bg-white p-6 shadow-2xl shadow-slate-300/40 sm:p-8">
            <div className="mb-6 flex items-center justify-between">
              <div>
                <p className="text-sm text-slate-500">Your progress</p>
                <p className="text-xl font-bold text-slate-900">Mock test #14</p>
              </div>
              <span className="rounded-full bg-blue-50 px-3 py-1 text-xs font-semibold text-blue-700">
                Academic
              </span>
            </div>

            <div className="space-y-4">
              {SKILLS.map((s, i) => (
                <div key={s.label}>
                  <div className="mb-1.5 flex items-center justify-between text-sm">
                    <span className="flex items-center gap-2 font-medium text-slate-700">
                      <s.icon className="h-4 w-4 text-slate-400" />
                      {s.label}
                    </span>
                    <span className="font-semibold text-slate-900">{s.band.toFixed(1)}</span>
                  </div>
                  <div className="h-2.5 overflow-hidden rounded-full bg-slate-100">
                    <motion.div
                      initial={{ width: 0 }}
                      animate={{ width: `${s.pct}%` }}
                      transition={{ duration: 1, ease: EASE, delay: 0.6 + i * 0.15 }}
                      className={`h-full rounded-full bg-gradient-to-r ${s.color}`}
                    />
                  </div>
                </div>
              ))}
            </div>
          </div>
        </motion.div>
      </div>
    </section>
  );
}
