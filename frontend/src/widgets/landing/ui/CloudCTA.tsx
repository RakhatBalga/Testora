"use client";

import Link from "next/link";
import { motion } from "framer-motion";
import { fadeUp, viewport } from "@/shared/lib/motion";
import Clouds from "./Clouds";

export default function CloudCTA() {
  return (
    <section className="px-4 pt-4 sm:px-6">
      <div className="relative mx-auto max-w-[1400px] overflow-hidden rounded-[32px] bg-gradient-to-b from-[#60a5fa] to-[#2563eb] py-24 sm:py-28">
        <Clouds />

        <motion.div
          initial="hidden"
          whileInView="show"
          viewport={viewport}
          variants={{ show: { transition: { staggerChildren: 0.12 } } }}
          className="relative mx-auto max-w-2xl px-6 text-center"
        >
          <motion.h2
            variants={fadeUp}
            className="text-4xl font-extrabold leading-[1.1] tracking-tight text-white sm:text-5xl"
          >
            Big bands start
            <br />
            with small sessions
          </motion.h2>

          <motion.div variants={fadeUp} className="mt-9">
            <Link
              href="/register"
              className="inline-flex h-14 items-center justify-center rounded-2xl bg-white px-10 text-base font-semibold text-slate-900 shadow-lg shadow-blue-900/20 transition-all duration-300 hover:-translate-y-0.5 hover:shadow-xl"
            >
              Try it
            </Link>
          </motion.div>
        </motion.div>
      </div>
    </section>
  );
}
