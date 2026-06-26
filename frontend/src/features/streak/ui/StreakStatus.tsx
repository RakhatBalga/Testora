"use client";

import Link from "next/link";
import { Flame } from "lucide-react";
import { type Streak } from "@/shared/api";

export function StreakStatus({ streak, href }: { streak: Streak | null; href: string }) {
  if (!streak) {
    return (
      <div className="h-11 w-20 animate-pulse rounded-xl border border-[var(--border)] bg-slate-50" />
    );
  }

  const active = streak.active_today;
  const days = streak.current_streak;
  const label = `${days} day${days === 1 ? "" : "s"} streak${
    active ? ", active today" : ", practice today to keep it"
  }`;

  return (
    <Link
      href={href}
      aria-label={label}
      title={label}
      className={`inline-flex h-11 items-center gap-2 rounded-xl border px-3 text-sm font-bold transition-colors ${
        active
          ? "border-amber-200 bg-amber-50/80 hover:bg-amber-50"
          : "border-[var(--border)] bg-white hover:border-slate-300 hover:bg-slate-50"
      }`}
    >
      <Flame className={`h-4 w-4 ${active ? "text-amber-500" : "text-slate-400"}`} />
      <span className={active ? "text-amber-700" : "text-[var(--text-primary)]"}>{days}d</span>
    </Link>
  );
}
