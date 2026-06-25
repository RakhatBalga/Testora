"use client";

import Link from "next/link";
import { motion } from "framer-motion";
import { ArrowRight } from "lucide-react";
import { fadeUp, viewport } from "./motion";

export default function CTA() {
  return (
    <section className="mx-auto max-w-6xl px-5 pb-24">
      <motion.div
        initial="hidden"
        whileInView="show"
        viewport={viewport}
        variants={fadeUp}
        className="relative overflow-hidden rounded-[32px] bg-slate-900 px-6 py-16 text-center sm:px-12"
      >
        <div className="pointer-events-none absolute -left-16 -top-16 h-64 w-64 rounded-full bg-blue-500/30 blur-3xl" />
        <div className="pointer-events-none absolute -bottom-20 -right-10 h-72 w-72 rounded-full bg-blue-400/20 blur-3xl" />

        <div className="relative">
          <h2 className="mx-auto max-w-xl text-3xl font-extrabold tracking-tight text-white sm:text-4xl">
            Ready to reach your target band?
          </h2>
          <p className="mx-auto mt-4 max-w-md text-slate-300">
            Create a free account and take your first practice test in minutes.
          </p>
          <div className="mt-8 flex justify-center">
            <Link
              href="/register"
              className="group inline-flex items-center gap-2 rounded-2xl bg-white px-7 py-4 text-base font-semibold text-slate-900 shadow-lg transition-all duration-300 hover:shadow-xl"
            >
              Get Started
              <ArrowRight className="h-5 w-5 transition-transform duration-300 group-hover:translate-x-1" />
            </Link>
          </div>
        </div>
      </motion.div>
    </section>
  );
}
