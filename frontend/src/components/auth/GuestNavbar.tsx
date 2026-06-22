"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

export default function GuestNavbar() {
  const pathname = usePathname();
  const onRegister = pathname === "/register";

  return (
    <header className="fixed inset-x-0 top-0 z-50 h-[70px] border-b border-slate-200 bg-white">
      <div className="mx-auto flex h-full max-w-6xl items-center justify-between px-5 sm:px-8">
        <Link href="/" className="group flex items-center gap-2.5">
          <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-[var(--brand)] text-sm font-bold text-white shadow-md shadow-[var(--brand)]/25 transition-transform duration-300 group-hover:scale-105">
            T
          </span>
          <span className="text-lg font-bold tracking-tight text-slate-900">Testora</span>
        </Link>

        <div className="flex items-center gap-2">
          <Link
            href="/login"
            className={`rounded-full px-4 py-2 text-sm font-semibold transition-colors ${
              onRegister
                ? "text-slate-600 hover:text-slate-900"
                : "text-slate-900"
            }`}
          >
            Login
          </Link>
          <Link
            href="/register"
            className={`rounded-full px-5 py-2.5 text-sm font-semibold transition-all duration-300 ${
              onRegister
                ? "bg-[var(--brand)] text-white shadow-sm hover:shadow-md"
                : "border border-slate-200 text-slate-700 hover:border-slate-300 hover:bg-slate-50"
            }`}
          >
            Register
          </Link>
        </div>
      </div>
    </header>
  );
}
