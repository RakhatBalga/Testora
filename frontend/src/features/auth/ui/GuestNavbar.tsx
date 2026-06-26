"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";

const LANGS = ["EN", "RU", "KZ"];

export default function GuestNavbar() {
  const pathname = usePathname();
  const onRegister = pathname === "/register";
  const [lang, setLang] = useState("EN");
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 8);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  return (
    <header
      className={`sticky inset-x-0 top-0 z-50 h-[76px] border-b transition-colors duration-300 ${
        scrolled
          ? "border-[var(--border)] bg-white/80 backdrop-blur-md"
          : "border-transparent bg-[var(--background)]"
      }`}
    >
      <div className="mx-auto flex h-full max-w-6xl items-center justify-between px-6 sm:px-8">
        <Link href="/" className="group flex items-center gap-2.5">
          <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-[var(--brand)] text-sm font-bold text-white shadow-sm shadow-[var(--brand)]/30 transition-transform duration-300 group-hover:scale-105">
            T
          </span>
          <span className="text-lg font-bold tracking-tight text-[var(--text-primary)]">
            Testora
          </span>
        </Link>

        <div className="flex items-center gap-3">
          <div className="hidden items-center rounded-full border border-[var(--border)] bg-white p-0.5 sm:inline-flex">
            {LANGS.map((l) => (
              <button
                key={l}
                type="button"
                onClick={() => setLang(l)}
                className={`rounded-full px-3 py-1 text-xs font-semibold transition-colors ${
                  lang === l
                    ? "bg-[var(--text-primary)] text-white"
                    : "text-[var(--text-secondary)] hover:text-[var(--text-primary)]"
                }`}
              >
                {l}
              </button>
            ))}
          </div>

          <span className="hidden h-5 w-px bg-[var(--border)] sm:block" />

          <Link
            href="/login"
            className={`rounded-full px-4 py-2 text-sm font-semibold transition-colors ${
              onRegister
                ? "text-[var(--text-secondary)] hover:text-[var(--text-primary)]"
                : "text-[var(--text-primary)]"
            }`}
          >
            Sign In
          </Link>
          <Link
            href="/register"
            className={`rounded-full px-5 py-2.5 text-sm font-semibold transition-all duration-300 ${
              onRegister
                ? "border border-[var(--border)] text-[var(--text-secondary)] hover:border-slate-300 hover:bg-white"
                : "bg-[var(--brand)] text-white shadow-sm shadow-[var(--brand)]/25 hover:bg-[var(--brand-dark)]"
            }`}
          >
            Get Started
          </Link>
        </div>
      </div>
    </header>
  );
}
