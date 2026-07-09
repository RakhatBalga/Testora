"use client";

import Link from "next/link";
import Clouds from "./Clouds";

export default function Hero() {
  return (
    <section className="px-4 pt-4 sm:px-6">
      <div className="relative mx-auto max-w-[1400px] overflow-hidden rounded-[32px] bg-gradient-to-b from-[#3b82f6] to-[#2563eb] pb-24 pt-28 sm:pb-32 sm:pt-36">
        <Clouds />

        {/* Content is visible by default and animated with CSS (not JS/rAF), so it
            never stays hidden in a backgrounded tab or if scripting is slow. */}
        <div className="relative z-10 mx-auto max-w-3xl px-6 text-center">
          <h1 className="animate-fade-up text-4xl font-extrabold leading-[1.08] tracking-tight text-white [text-shadow:0_2px_20px_rgba(15,23,42,0.25)] sm:text-6xl">
            Practice what actually
            <br />
            moves your band
          </h1>

          <p className="animate-fade-up mx-auto mt-6 max-w-xl text-lg leading-relaxed text-white/95 [animation-delay:120ms] sm:text-xl">
            An AI coach that grades your work, finds what blocks your score,
            and tells you exactly what to practise today.
          </p>

          <div className="animate-fade-up mt-10 [animation-delay:240ms]">
            <Link
              href="/register"
              className="inline-flex h-14 items-center justify-center rounded-2xl bg-white px-10 text-base font-bold text-[var(--brand)] shadow-xl shadow-blue-950/25 ring-1 ring-white/60 transition-all duration-300 hover:-translate-y-0.5 hover:bg-blue-50 hover:shadow-2xl"
            >
              Try it for free
            </Link>
          </div>
        </div>
      </div>
    </section>
  );
}
