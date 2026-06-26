"use client";

import { useEffect, useMemo, useState } from "react";
import { api, type AttemptSummary, type Test } from "@/shared/api";
import { useRequireAuth } from "@/shared/auth";
import { Skeleton } from "@/shared/ui";
import { ContinueCard, RecentActivity, TestCard } from "@/entities/test";
import { accentFor, deriveProgress, type TestProgress } from "@/entities/test";

export default function ListeningLibraryPage() {
  const { token, ready } = useRequireAuth();
  const accent = accentFor("listening");
  const [tests, setTests] = useState<Test[]>([]);
  const [attempts, setAttempts] = useState<AttemptSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!token) return;
    Promise.all([api.listTests(), api.listAttempts()])
      .then(([allTests, allAttempts]) => {
        setTests(allTests.filter((test) => test.test_type === "listening"));
        setAttempts(allAttempts.filter((attempt) => attempt.test_type === "listening"));
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [token]);

  const progressById = useMemo(() => {
    const map = new Map<number, TestProgress>();
    for (const test of tests) map.set(test.id, deriveProgress(test, attempts));
    return map;
  }, [tests, attempts]);

  const continueTest = useMemo(() => {
    const inProgress = tests
      .map((test) => ({ test, progress: progressById.get(test.id)! }))
      .filter((item) => item.progress?.status === "in_progress");
    inProgress.sort((a, b) => (b.progress.updatedAt ?? 0) - (a.progress.updatedAt ?? 0));
    return inProgress[0] ?? null;
  }, [tests, progressById]);

  if (!ready || !token) return null;

  return (
    <div className="mx-auto max-w-6xl space-y-10">
      <header className="animate-fade-up">
        <p className={`text-sm font-semibold uppercase tracking-wider ${accent.text}`}>
          Listening
        </p>
        <h1 className="mt-1 text-3xl font-extrabold tracking-tight text-slate-900">
          IELTS Listening Practice
        </h1>
        <p className="mt-2 max-w-2xl text-slate-500">
          Complete timed listening sections with audio, transcript-backed explanations, and band estimates.
        </p>
      </header>

      {error && <p className="rounded-xl bg-red-50 px-4 py-3 text-sm text-red-600">{error}</p>}

      {!loading && continueTest && (
        <ContinueCard
          test={continueTest.test}
          href={`/listening/${continueTest.test.id}`}
          progress={continueTest.progress}
        />
      )}

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
            No listening tests available yet.
          </div>
        ) : (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {tests.map((test) => (
              <TestCard
                key={test.id}
                test={test}
                href={`/listening/${test.id}`}
                progress={progressById.get(test.id)!}
              />
            ))}
          </div>
        )}
      </section>

      {!loading && <RecentActivity attempts={attempts} />}
    </div>
  );
}
