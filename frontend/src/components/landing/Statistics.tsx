"use client";

import { useEffect, useRef, useState } from "react";
import { motion, useInView } from "framer-motion";
import { BookOpen, FileText, ListChecks, SearchCheck, type LucideIcon } from "lucide-react";
import { fadeUp, stagger, viewport } from "./motion";

type Stat = {
  icon: LucideIcon;
  value: number;
  suffix: string;
  label: string;
};

const STATS: Stat[] = [
  { icon: BookOpen, value: 10, suffix: "", label: "Academic Reading tests" },
  { icon: FileText, value: 30, suffix: "", label: "Original passages" },
  { icon: SearchCheck, value: 400, suffix: "", label: "Evidence-backed questions" },
  { icon: ListChecks, value: 40, suffix: "", label: "Questions per test" },
];

function format(n: number) {
  if (n >= 1000) return `${(n / 1000).toFixed(n % 1000 === 0 ? 0 : 1)}k`;
  return String(n);
}

function Counter({ value, suffix }: { value: number; suffix: string }) {
  const ref = useRef<HTMLSpanElement>(null);
  const inView = useInView(ref, { once: true, margin: "-60px" });
  const [n, setN] = useState(0);

  useEffect(() => {
    if (!inView) return;
    let raf = 0;
    const start = performance.now();
    const dur = 1400;
    const tick = (now: number) => {
      const t = Math.min((now - start) / dur, 1);
      const eased = 1 - Math.pow(1 - t, 3);
      setN(Math.round(value * eased));
      if (t < 1) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [inView, value]);

  return (
    <span ref={ref}>
      {format(n)}
      {suffix}
    </span>
  );
}

export default function Statistics() {
  return (
    <section className="mx-auto max-w-6xl px-5 py-20 lg:py-24">
      <motion.div
        initial="hidden"
        whileInView="show"
        viewport={viewport}
        variants={stagger}
        className="overflow-hidden rounded-[32px] bg-[var(--brand)] px-6 py-12 shadow-2xl shadow-blue-500/25 sm:px-12"
      >
        <div className="grid gap-8 sm:grid-cols-2 lg:grid-cols-4">
          {STATS.map((s) => (
            <motion.div key={s.label} variants={fadeUp} className="text-center">
              <span className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-2xl bg-white/15 text-white backdrop-blur">
                <s.icon className="h-6 w-6" />
              </span>
              <p className="text-4xl font-extrabold tracking-tight text-white sm:text-5xl">
                <Counter value={s.value} suffix={s.suffix} />
              </p>
              <p className="mt-1 text-sm font-medium text-indigo-100">{s.label}</p>
            </motion.div>
          ))}
        </div>
      </motion.div>
    </section>
  );
}
