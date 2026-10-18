"use client";

import { useEffect, useMemo, useState } from "react";
import { api, type AttemptSummary, type Test, type ListeningProgress } from "@/shared/api";
import { useRequireAuth } from "@/shared/auth";
import { Skeleton } from "@/shared/ui";
import { ContinueCard, RecentActivity, TestCard } from "@/entities/test";
import { accentFor, deriveProgress, type TestProgress } from "@/entities/test";

import { listeningSessionKey, restoreProgress } from "@/features/listening-session/progress";

export default function ListeningLibraryPage() {
  const { token, ready } = useRequireAuth();
  const accent = accentFor("listening");
  const [tests, setTests] = useState<Test[]>([]);
  const [savedProgress, setSavedProgress] = useState<Record<number, ListeningProgress | null>>({});
  const [attempts, setAttempts] = useState<AttemptSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!token) return;
    let cancelled = false;
    Promise.all([api.listListeningTests(), api.listAttempts()])
      .then(async ([listeningTests, allAttempts]) => {
        if (cancelled) return;
        setTests(listeningTests.map((test) => ({ ...test, test_type: "listening" })));
        setAttempts(allAttempts.filter((attempt) => attempt.test_type === "listening"));
        const progress = await Promise.all(listeningTests.map(async (test) => [test.id,
          restoreProgress(listeningSessionKey(test.id, test.content_version),
            await api.getListeningProgress(test.id, test.content_version, "practice"))] as const));
        if (cancelled) return;
        setSavedProgress(Object.fromEntries(progress));
      })
      .catch((err) => { if (!cancelled) setError(err.message); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [token]);

  const progressById = useMemo(() => {
    const map = new Map<number, TestProgress>();
    for (const test of tests) {
      const saved = savedProgress[test.id];
      if (saved) {
        const answered = Object.values(saved.answers).filter((value) => Array.isArray(value) ? value.length > 0 : typeof value === "string" && value.trim() !== "").length;
        map.set(test.id, { status: "in_progress", answered,
          ratio: test.question_count ? Math.min(1, answered / test.question_count) : 0,
          updatedAt: Date.parse(saved.updated_at), band: null });
      } else {
        map.set(test.id, deriveProgress(test, attempts));
      }
    }
    return map;
  }, [tests, attempts, savedProgress]);

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
          Testora Listening Practice
        </h1>
        <p className="mt-2 max-w-2xl text-slate-500">
          Complete an original four-section test in Exam or Practice mode, then review timestamped evidence.
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
