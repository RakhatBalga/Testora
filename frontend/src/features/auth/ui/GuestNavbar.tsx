"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import Image from "next/image";
import { usePathname } from "next/navigation";

export default function GuestNavbar() {
  const pathname = usePathname();
  const onRegister = pathname === "/register";
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
          <Image
            src="/logo.svg"
            alt="Testora"
            width={36}
            height={36}
            priority
            className="h-9 w-9 object-contain transition-transform duration-300 group-hover:scale-105"
          />
          <span className="text-lg font-bold tracking-tight text-[var(--text-primary)]">
            Testora
          </span>
        </Link>

        <div className="flex items-center gap-3">
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
