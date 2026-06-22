"use client";

import { useEffect, useState, ReactNode } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { Card } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Skeleton } from "@/components/ui/Skeleton";
import Landing from "@/components/landing/Landing";

export default function HomePage() {
  const { token, username, ready } = useAuth();

  if (!ready) return null;
  return token ? <Dashboard username={username} /> : <Landing />;
}

/* ----------------------------------------------------------------------- */
/* Category definitions for the "Tests" hub                                */
/* ----------------------------------------------------------------------- */
type CategoryKey = "reading" | "listening" | "writing" | "speaking";

type Category = {
  key: CategoryKey;
  title: string;
  description: string;
  href: string;
  badge: "blue" | "violet" | "green" | "slate";
  gradient: string;
  hover: string;
  icon: ReactNode;
};

const CATEGORIES: Category[] = [
  {
    key: "reading",
    title: "Reading",
    description: "Academic passages with mixed IELTS question types.",
    href: "/tests/reading",
    badge: "blue",
    gradient: "from-blue-500 to-indigo-500",
    hover: "group-hover:border-blue-300",
    icon: (
      <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M12 6.5C10.5 5.3 8.5 4.8 6 4.8c-1 0-2 .1-3 .4v13c1-.3 2-.4 3-.4 2.5 0 4.5.5 6 1.7 1.5-1.2 3.5-1.7 6-1.7 1 0 2 .1 3 .4v-13c-1-.3-2-.4-3-.4-2.5 0-4.5.5-6 1.7Z" />
        <path strokeLinecap="round" strokeLinejoin="round" d="M12 6.5V19" />
      </svg>
    ),
  },
  {
    key: "listening",
    title: "Listening",
    description: "Audio clips with comprehension questions and a timer.",
    href: "/tests/listening",
    badge: "violet",
    gradient: "from-violet-500 to-purple-500",
    hover: "group-hover:border-violet-300",
    icon: (
      <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M4 13a8 8 0 0 1 16 0" />
        <path strokeLinecap="round" strokeLinejoin="round" d="M4 13v3a2 2 0 0 0 2 2h1v-5H6a2 2 0 0 0-2 2Zm16 0v3a2 2 0 0 1-2 2h-1v-5h1a2 2 0 0 1 2 2Z" />
      </svg>
    ),
  },
  {
    key: "writing",
    title: "Writing",
    description: "Task 1 & Task 2 prompts with instant AI band feedback.",
    href: "/writing",
    badge: "green",
    gradient: "from-emerald-500 to-teal-500",
    hover: "group-hover:border-emerald-300",
    icon: (
      <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M16.5 4.5l3 3L8 19l-4 1 1-4L16.5 4.5Z" />
        <path strokeLinecap="round" strokeLinejoin="round" d="M14.5 6.5l3 3" />
      </svg>
    ),
  },
  {
    key: "speaking",
    title: "Speaking",
    description: "Record answers across all three speaking parts.",
    href: "/speaking",
    badge: "slate",
    gradient: "from-amber-500 to-orange-500",
    hover: "group-hover:border-amber-300",
    icon: (
      <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}>
        <rect x="9" y="3" width="6" height="11" rx="3" />
        <path strokeLinecap="round" strokeLinejoin="round" d="M5 11a7 7 0 0 0 14 0M12 18v3" />
      </svg>
    ),
  },
];

/* ----------------------------------------------------------------------- */
/* Dashboard (logged in) — the "Tests" hub                                 */
/* ----------------------------------------------------------------------- */
function Dashboard({ username }: { username: string | null }) {
  const [counts, setCounts] = useState<Record<CategoryKey, number> | null>(null);
  const [stats, setStats] = useState<{
    taken: number;
    avgBand: number | null;
    bestBand: number | null;
  } | null>(null);

  useEffect(() => {
    Promise.all([
      api.listTests(),
      api.listWritingTasks(),
      api.listSpeakingTasks(),
      api.listAttempts(),
      api.listWritingSubmissions(),
      api.listSpeakingSubmissions(),
    ])
      .then(([tests, writing, speaking, attempts, writingSubs, speakingSubs]) => {
        setCounts({
          reading: tests.filter((t) => t.test_type === "reading").length,
          listening: tests.filter((t) => t.test_type === "listening").length,
          writing: writing.length,
          speaking: speaking.length,
        });
        // IELTS 0–9 band averaged across every graded item, rounded to 0.5.
        const bands = [
          ...attempts.map((a) => a.band),
          ...writingSubs.map((w) => w.band),
          ...speakingSubs.map((s) => s.band),
        ].filter((b): b is number => b !== null);
        const avgBand =
          bands.length === 0
            ? null
            : Math.round((bands.reduce((s, b) => s + b, 0) / bands.length) * 2) / 2;
        const bestBand = bands.length === 0 ? null : Math.max(...bands);
        setStats({ taken: attempts.length, avgBand, bestBand });
      })
      .catch(() => {
        setCounts({ reading: 0, listening: 0, writing: 0, speaking: 0 });
        setStats({ taken: 0, avgBand: null, bestBand: null });
      });
  }, []);

  return (
    <div className="space-y-10">
      <div className="animate-fade-up">
        <h1 className="text-2xl font-bold text-slate-900 sm:text-3xl">
          Welcome back{username ? `, ${username}` : ""} 👋
        </h1>
        <p className="mt-1 text-slate-500">Choose a section below and keep practising.</p>
      </div>

      <div className="grid animate-fade-up gap-4 [animation-delay:80ms] sm:grid-cols-3">
        <StatCard label="Tests taken" value={stats ? String(stats.taken) : null} />
        <StatCard
          label="Average band"
          value={stats ? (stats.avgBand === null ? "—" : stats.avgBand.toFixed(1)) : null}
        />
        <StatCard
          label="Best band"
          value={stats ? (stats.bestBand === null ? "—" : stats.bestBand.toFixed(1)) : null}
        />
      </div>

      <section>
        <h2 className="mb-4 text-lg font-semibold text-slate-900">Tests</h2>
        <div className="grid gap-4 sm:grid-cols-2">
          {CATEGORIES.map((cat, i) => (
            <Link
              key={cat.key}
              href={cat.href}
              className="group animate-fade-up"
              style={{ animationDelay: `${120 + i * 90}ms` }}
            >
              <Card
                className={`flex h-full items-start gap-4 p-5 transition duration-300 group-hover:-translate-y-1 group-hover:shadow-lg ${cat.hover}`}
              >
                <span
                  className={`flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br text-white shadow-sm transition-transform duration-300 group-hover:scale-110 ${cat.gradient}`}
                >
                  {cat.icon}
                </span>
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <h3 className="text-lg font-semibold text-slate-900">
                      {cat.title}
                    </h3>
                    {counts && (
                      <Badge tone={cat.badge}>
                        {counts[cat.key]}{" "}
                        {cat.key === "writing" || cat.key === "speaking"
                          ? "tasks"
                          : "tests"}
                      </Badge>
                    )}
                  </div>
                  <p className="mt-1 text-sm leading-relaxed text-slate-500">
                    {cat.description}
                  </p>
                </div>
                <span className="self-center text-slate-300 transition-transform duration-300 group-hover:translate-x-1 group-hover:text-slate-500">
                  <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M9 6l6 6-6 6" />
                  </svg>
                </span>
              </Card>
            </Link>
          ))}
        </div>
      </section>
    </div>
  );
}

function StatCard({ label, value }: { label: string; value: string | null }) {
  return (
    <Card className="p-5">
      <p className="text-sm text-slate-500">{label}</p>
      {value === null ? (
        <Skeleton className="mt-2 h-8 w-16" />
      ) : (
        <p className="mt-1 text-3xl font-bold text-slate-900">{value}</p>
      )}
    </Card>
  );
}
