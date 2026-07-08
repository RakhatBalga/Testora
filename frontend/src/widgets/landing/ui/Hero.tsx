"use client";

import Link from "next/link";
import { motion } from "framer-motion";
import { fadeUp } from "@/shared/lib/motion";
import Clouds from "./Clouds";

export default function Hero() {
  return (
    <section className="px-4 pt-4 sm:px-6">
      <div className="relative mx-auto max-w-[1400px] overflow-hidden rounded-[32px] bg-gradient-to-b from-[#3b82f6] to-[#2563eb] pb-24 pt-28 sm:pb-32 sm:pt-36">
        <Clouds />

        <motion.div
          initial="hidden"
          animate="show"
          variants={{ show: { transition: { staggerChildren: 0.12 } } }}
          className="relative mx-auto max-w-3xl px-6 text-center"
        >
          <motion.h1
            variants={fadeUp}
            className="text-4xl font-extrabold leading-[1.08] tracking-tight text-white sm:text-6xl"
          >
            Practice what actually
            <br />
            moves your band
          </motion.h1>

          <motion.p
            variants={fadeUp}
            className="mx-auto mt-6 max-w-xl text-lg leading-relaxed text-white/85 sm:text-xl"
          >
            An AI coach that grades your work, finds what blocks your score,
            and tells you exactly what to practise today.
          </motion.p>

          <motion.div variants={fadeUp} className="mt-10">
            <Link
              href="/register"
              className="inline-flex h-14 items-center justify-center rounded-2xl bg-white px-10 text-base font-semibold text-slate-900 shadow-lg shadow-blue-900/20 transition-all duration-300 hover:-translate-y-0.5 hover:shadow-xl hover:shadow-blue-900/25"
            >
              Try it for free
            </Link>
          </motion.div>
        </motion.div>
      </div>
    </section>
  );
}
