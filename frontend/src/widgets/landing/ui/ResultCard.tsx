"use client";

import { motion } from "framer-motion";
import { viewport, EASE } from "@/shared/lib/motion";

/** CSS/SVG dartboard illustration — bullseye hit, drawn in brand blues. */
function Target() {
  return (
    <svg viewBox="0 0 420 420" className="h-full w-full" aria-hidden>
      <circle cx="150" cy="230" r="190" fill="#dbeafe" />
      <circle cx="150" cy="230" r="145" fill="#bfdbfe" />
      <circle cx="150" cy="230" r="100" fill="#93c5fd" />
      <circle cx="150" cy="230" r="58" fill="#dbeafe" />
      <ellipse cx="150" cy="230" rx="26" ry="30" fill="#3b82f6" />
      {/* dart */}
      <g transform="rotate(38 290 130)">
        <rect x="230" y="122" width="130" height="14" rx="7" fill="#2563eb" />
        <path d="M352 116 L392 129 L352 142 Z" fill="#60a5fa" />
        <path d="M230 129 L162 236 L172 240 Z" fill="#94a3b8" opacity="0.55" />
      </g>
    </svg>
  );
}

export default function ResultCard() {
  return (
    <section className="px-4 pt-4 sm:px-6">
      <div className="relative mx-auto max-w-[1400px] overflow-hidden rounded-[32px] bg-white">
        <div className="grid items-center gap-8 lg:grid-cols-2">
          <motion.div
            initial={{ opacity: 0, x: -60 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={viewport}
            transition={{ duration: 0.8, ease: EASE }}
            className="relative h-[320px] overflow-hidden sm:h-[420px]"
          >
            <div className="absolute -bottom-24 -left-16 h-[130%] w-full max-w-[480px]">
              <Target />
            </div>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, x: 60 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={viewport}
            transition={{ duration: 0.8, ease: EASE, delay: 0.1 }}
            className="px-6 pb-14 text-center lg:pb-0 lg:pr-16 lg:text-right"
          >
            <h2 className="text-4xl font-extrabold tracking-tight text-slate-900 sm:text-5xl">
              Aimed at your blocker
            </h2>
            <p className="mt-6 text-xl leading-relaxed text-slate-500 sm:text-2xl">
              Testora names the exact criterion holding your band down — and
              builds today&apos;s practice around fixing it.
            </p>
          </motion.div>
        </div>
      </div>
    </section>
  );
}
