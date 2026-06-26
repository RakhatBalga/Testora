"use client";

import { useEffect, useMemo, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { api, type AttemptResult, type TestDetail } from "@/shared/api";
import { useRequireAuth } from "@/shared/auth";
import { Card, Skeleton } from "@/shared/ui";
import { buildGroups } from "@/features/reading-session";
import { ReadingReview } from "@/features/reading-session";

export default function ListeningResultPage() {
  const { token, ready } = useRequireAuth();
  const router = useRouter();
  const params = useParams();
  const attemptId = Number(params?.id);

  const [result, setResult] = useState<AttemptResult | null>(null);
  const [test, setTest] = useState<TestDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!token) return;
    let cancelled = false;
    (async () => {
      try {
        const attempt = await api.getAttempt(attemptId);
        const detail = await api.getTest(attempt.test_id);
        if (cancelled) return;
        setResult(attempt);
        setTest(detail);
      } catch (err) {
        if (!cancelled) setError(err instanceof Error ? err.message : "Failed to load result");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [token, attemptId]);

  const groups = useMemo(() => (test ? buildGroups(test) : []), [test]);

  const retake = () => {
    if (!result) return;
    localStorage.removeItem(`listening-${result.test_id}-result`);
    localStorage.removeItem(`listening-${result.test_id}-answers`);
    localStorage.removeItem(`listening-${result.test_id}-updated`);
    router.push(`/listening/${result.test_id}`);
  };

  if (!ready || !token) return null;
  if (loading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-44 w-full" />
        <Skeleton className="h-64 w-full" />
      </div>
    );
  }
  if (error) {
    return <p className="rounded-xl bg-red-50 px-4 py-3 text-sm text-red-600">{error}</p>;
  }
  if (!result || !test || groups.length === 0) {
    return <Card className="p-8 text-center text-slate-500">Listening result is unavailable.</Card>;
  }

  return <ReadingReview result={result} groups={groups} onRetake={retake} />;
}
