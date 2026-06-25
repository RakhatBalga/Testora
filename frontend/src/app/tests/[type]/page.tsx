"use client";

import { useEffect, useMemo, useState } from "react";
import { useParams, notFound } from "next/navigation";
import { api, type AttemptSummary, type Test } from "@/lib/api";
import { useRequireAuth } from "@/hooks/useRequireAuth";
import { Skeleton } from "@/components/ui/Skeleton";
import { ContinueCard } from "@/components/library/ContinueCard";
import { TestCard } from "@/components/library/TestCard";
import { RecentActivity } from "@/components/library/RecentActivity";
import { accentFor, deriveProgress, type TestProgress } from "@/components/library/library";

const META: Record<string, { eyebrow: string; title: string; description: string }> = {
  reading: {
    eyebrow: "Reading",
    title: "Academic IELTS Reading Practice",
    description: "Improve speed, accuracy and band score through realistic IELTS passages.",
  },
  listening: {
    eyebrow: "Listening",
    title: "Academic IELTS Listening Practice",
    description: "Sharpen comprehension and note-taking with full, timed listening sets.",
  },
};

function examHref(test: Test): string {
  if (test.test_type === "reading") return `/reading/${test.id}`;
  if (test.test_type === "listening") return `/listening/${test.id}`;
  return `/test/${test.id}`;
}

export default function TestLibraryPage() {
  const { token, ready } = useRequireAuth();
  const params = useParams();
  const type = String(params.type);
  const meta = META[type];
  const accent = accentFor(type);

  const [tests, setTests] = useState<Test[]>([]);
  const [attempts, setAttempts] = useState<AttemptSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!token || !meta) return;
    Promise.all([api.listTests(), api.listAttempts()])
      .then(([allTests, allAttempts]) => {
        setTests(allTests.filter((t) => t.test_type === type));
        setAttempts(allAttempts.filter((a) => a.test_type === type));
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [token, type, meta]);

  // Derive per-test progress once (reads localStorage), keyed by test id.
  const progressById = useMemo(() => {
    const map = new Map<number, TestProgress>();
    for (const t of tests) map.set(t.id, deriveProgress(t, attempts));
    return map;
  }, [tests, attempts]);

  // Most recent in-progress test → "Continue last session".
  const continueTest = useMemo(() => {
    const inProgress = tests
      .map((t) => ({ test: t, p: progressById.get(t.id)! }))
      .filter((x) => x.p?.status === "in_progress");
    inProgress.sort((a, b) => (b.p.updatedAt ?? 0) - (a.p.updatedAt ?? 0));
    return inProgress[0] ?? null;
  }, [tests, progressById]);

  if (!meta) return notFound();
  if (!ready || !token) return null;

  return (
    <div className="mx-auto max-w-6xl space-y-10">
      {/* SECTION 1 — HERO */}
      <header className="animate-fade-up">
        <p className={`text-sm font-semibold uppercase tracking-wider ${accent.text}`}>
          {meta.eyebrow}
        </p>
        <h1 className="mt-1 text-3xl font-extrabold tracking-tight text-slate-900">
          {meta.title}
        </h1>
        <p className="mt-2 max-w-2xl text-slate-500">{meta.description}</p>
      </header>

      {error && <p className="rounded-xl bg-red-50 px-4 py-3 text-sm text-red-600">{error}</p>}

      {/* SECTION 2 — CONTINUE LEARNING */}
      {!loading && continueTest && (
        <div className="animate-fade-up">
          <ContinueCard
            test={continueTest.test}
            href={examHref(continueTest.test)}
            progress={continueTest.p}
          />
        </div>
      )}

      {/* SECTION 4 — LIBRARY */}
      <section className="space-y-4">
        <h2 className="text-lg font-bold text-slate-900">Test library</h2>

        {loading ? (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {[0, 1, 2].map((i) => (
              <Skeleton key={i} className="h-44 w-full rounded-2xl" />
            ))}
          </div>
        ) : tests.length === 0 ? (
          <div className="rounded-2xl bg-white px-6 py-12 text-center text-slate-500 shadow-sm ring-1 ring-slate-100">
            No {meta.eyebrow.toLowerCase()} tests available yet.
          </div>
        ) : (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {tests.map((t) => (
              <TestCard
                key={t.id}
                test={t}
                href={examHref(t)}
                progress={progressById.get(t.id)!}
              />
            ))}
          </div>
        )}
      </section>

      {/* SECTION 5 — RECENT ACTIVITY */}
      {!loading && <RecentActivity attempts={attempts} />}
    </div>
  );
}
