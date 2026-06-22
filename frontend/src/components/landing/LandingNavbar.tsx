"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { motion, AnimatePresence } from "framer-motion";
import { Menu, X } from "lucide-react";

const LINKS = [
  { label: "Features", href: "#features" },
  { label: "Tests", href: "#showcase" },
  { label: "Reviews", href: "#testimonials" },
  { label: "FAQ", href: "#faq" },
];

export default function LandingNavbar() {
  const [scrolled, setScrolled] = useState(false);
  const [open, setOpen] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 8);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  return (
    <header
      className={`sticky top-0 z-50 transition-all duration-300 ${
        scrolled
          ? "border-b border-slate-200/70 bg-white/75 shadow-sm backdrop-blur-xl"
          : "border-b border-transparent bg-transparent"
      }`}
    >
      <nav className="mx-auto flex max-w-6xl items-center justify-between px-5 py-3.5">
        {/* Logo */}
        <Link href="/" className="group flex items-center gap-2.5" onClick={() => setOpen(false)}>
          <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-indigo-500 to-violet-600 text-sm font-bold text-white shadow-md shadow-indigo-500/25 transition-transform duration-300 group-hover:scale-105">
            T
          </span>
          <span className="text-lg font-bold tracking-tight text-slate-900">Testora</span>
        </Link>

        {/* Desktop links */}
        <div className="hidden items-center gap-1 md:flex">
          {LINKS.map((l) => (
            <a
              key={l.href}
              href={l.href}
              className="rounded-full px-4 py-2 text-sm font-medium text-slate-600 transition-colors hover:bg-slate-100 hover:text-slate-900"
            >
              {l.label}
            </a>
          ))}
        </div>

        {/* Desktop auth */}
        <div className="hidden items-center gap-2 md:flex">
          <Link
            href="/login"
            className="rounded-full px-4 py-2 text-sm font-semibold text-slate-700 transition-colors hover:text-slate-900"
          >
            Login
          </Link>
          <Link
            href="/register"
            className="rounded-full bg-slate-900 px-5 py-2.5 text-sm font-semibold text-white shadow-sm transition-all duration-300 hover:bg-slate-800 hover:shadow-md"
          >
            Register
          </Link>
        </div>

        {/* Mobile toggle */}
        <button
          type="button"
          onClick={() => setOpen((v) => !v)}
          aria-label="Toggle menu"
          className="flex h-10 w-10 items-center justify-center rounded-xl text-slate-700 transition-colors hover:bg-slate-100 md:hidden"
        >
          {open ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
        </button>
      </nav>

      {/* Mobile menu */}
      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.25, ease: "easeInOut" }}
            className="overflow-hidden border-t border-slate-200/70 bg-white/95 backdrop-blur-xl md:hidden"
          >
            <div className="mx-auto flex max-w-6xl flex-col gap-1 px-5 py-4">
              {LINKS.map((l) => (
                <a
                  key={l.href}
                  href={l.href}
                  onClick={() => setOpen(false)}
                  className="rounded-xl px-4 py-3 text-sm font-medium text-slate-700 transition-colors hover:bg-slate-100"
                >
                  {l.label}
                </a>
              ))}
              <div className="mt-2 flex gap-2">
                <Link
                  href="/login"
                  onClick={() => setOpen(false)}
                  className="flex-1 rounded-xl border border-slate-200 px-4 py-3 text-center text-sm font-semibold text-slate-700"
                >
                  Login
                </Link>
                <Link
                  href="/register"
                  onClick={() => setOpen(false)}
                  className="flex-1 rounded-xl bg-slate-900 px-4 py-3 text-center text-sm font-semibold text-white"
                >
                  Register
                </Link>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </header>
  );
}
