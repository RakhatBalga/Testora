"use client";

import { useEffect, useRef, useState } from "react";
import { motion, useInView } from "framer-motion";
import { EASE } from "@/shared/lib/motion";

/** Animated 6.0 → 7.5 counter that ticks up in half-band steps. */
function BandCounter() {
  const ref = useRef<HTMLSpanElement>(null);
  const inView = useInView(ref, { once: true, margin: "-80px" });
  const [band, setBand] = useState(6.0);

  useEffect(() => {
    if (!inView) return;
    let raf = 0;
    const start = performance.now();
    const dur = 1800;
    const tick = (now: number) => {
      const t = Math.min((now - start) / dur, 1);
      const eased = 1 - Math.pow(1 - t, 3);
      setBand(Math.round((6.0 + 1.5 * eased) * 2) / 2);
      if (t < 1) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [inView]);

  return <span ref={ref}>{band.toFixed(1)}</span>;
}

/** Rising band-score curve that draws itself on scroll, alims-style. */
export default function StatBand() {
  const ref = useRef<HTMLDivElement>(null);
  const inView = useInView(ref, { once: true, margin: "-120px" });

  const points = [
    { x: 40, y: 150 },
    { x: 220, y: 132 },
    { x: 420, y: 104 },
    { x: 620, y: 88 },
    { x: 820, y: 56 },
    { x: 1020, y: 22 },
  ];

  return (
    <section className="px-4 pt-4 sm:px-6">
      <div
        ref={ref}
        className="relative mx-auto max-w-[1400px] overflow-hidden rounded-[32px] bg-gradient-to-b from-[#60a5fa] to-[#3b82f6] px-6 pb-0 pt-14 text-center sm:pt-16"
      >
        <motion.p
          initial={{ opacity: 0, y: 18 }}
          animate={inView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.6, ease: EASE }}
          className="mx-auto max-w-2xl text-xl font-medium italic text-white/90 sm:text-2xl"
        >
          Every session ends with one answer: what to do next
        </motion.p>

        <motion.p
          initial={{ opacity: 0, y: 24, scale: 0.94 }}
          animate={inView ? { opacity: 1, y: 0, scale: 1 } : {}}
          transition={{ duration: 0.7, ease: EASE, delay: 0.15 }}
          className="mt-6 text-[7rem] font-extrabold leading-none tracking-tight text-white sm:text-[11rem]"
        >
          <BandCounter />
        </motion.p>
        <motion.p
          initial={{ opacity: 0 }}
          animate={inView ? { opacity: 1 } : {}}
          transition={{ duration: 0.6, delay: 0.5 }}
          className="mt-2 pb-6 text-sm font-semibold uppercase tracking-widest text-white/70"
        >
          your band, climbing week by week
        </motion.p>

        {/* self-drawing growth curve */}
        <svg
          viewBox="0 0 1060 170"
          fill="none"
          className="mx-auto -mb-1 block w-full max-w-5xl"
          aria-hidden
        >
          <motion.path
            d="M 40 150 C 160 145, 180 138, 220 132 C 320 118, 340 112, 420 104 C 520 94, 540 94, 620 88 C 720 80, 760 68, 820 56 C 900 40, 960 30, 1020 22"
            stroke="white"
            strokeWidth="4"
            strokeLinecap="round"
            initial={{ pathLength: 0 }}
            animate={inView ? { pathLength: 1 } : {}}
            transition={{ duration: 1.8, ease: "easeInOut", delay: 0.3 }}
          />
          {points.map((p, i) => (
            <motion.circle
              key={i}
              cx={p.x}
              cy={p.y}
              r="9"
              fill="white"
              initial={{ scale: 0, opacity: 0 }}
              animate={inView ? { scale: 1, opacity: 1 } : {}}
              transition={{ duration: 0.35, ease: EASE, delay: 0.4 + i * 0.28 }}
            />
          ))}
        </svg>
      </div>
    </section>
  );
}
