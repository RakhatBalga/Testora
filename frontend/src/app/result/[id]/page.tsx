"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { CheckCircle2, XCircle, Target, Clock, Percent, Flag } from "lucide-react";
import { api, AttemptResult } from "@/shared/api";
import { useRequireAuth } from "@/shared/auth";
import { Card } from "@/shared/ui";
import { LinkButton } from "@/shared/ui";
import { Skeleton } from "@/shared/ui";
import { ResultBreakdown } from "@/features/test-session";

function formatDuration(seconds: number | null): string | null {
  if (seconds == null) return null;
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return m > 0 ? `${m}m ${s}s` : `${s}s`;
}

export default function ResultPage() {
  const { token, ready } = useRequireAuth();
  const params = useParams();
  const attemptId = Number(params?.id);

  const [result, setResult] = useState<AttemptResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!token) return;
    api
      .getAttempt(attemptId)
      .then(setResult)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [token, attemptId]);

  if (!ready || !token) return null;
  if (loading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-48 w-full" />
        <Skeleton className="h-32 w-full" />
        <Skeleton className="h-24 w-full" />
      </div>
    );
  }
  if (error) {
    return <p className="rounded-xl bg-red-50 px-4 py-3 text-sm text-red-600">{error}</p>;
  }
  if (!result) return null;

  const band = result.band;
  const bandTone =
    band === null
      ? "text-slate-400"
      : band >= 7
        ? "text-green-600"
        : band >= 5.5
          ? "text-amber-600"
          : "text-red-600";
  const duration = formatDuration(result.duration_seconds);

  return (
    <div className="space-y-8">
      {/* hero: band + headline stats */}
      <Card className="overflow-hidden">
        <div className="bg-hero p-8 text-center">
          <p className="text-sm font-medium text-slate-500">{result.test_title}</p>
          {band !== null && (
            <>
              <p className="mt-4 text-xs font-semibold uppercase tracking-wide text-slate-400">
                Estimated IELTS band
              </p>
              <p className={`text-6xl font-extrabold ${bandTone}`}>{band.toFixed(1)}</p>
            </>
          )}
          <p className="mt-3 text-slate-500">
            {result.score} / {result.total} correct ({result.accuracy}%)
          </p>
        </div>
      </Card>

      {/* stat strip */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard icon={<Target className="h-5 w-5" />} label="Raw score" value={`${result.score}/${result.total}`} />
        <StatCard icon={<CheckCircle2 className="h-5 w-5" />} label="Correct" value={String(result.correct)} accent="text-emerald-600" />
        <StatCard icon={<XCircle className="h-5 w-5" />} label="Incorrect" value={String(result.incorrect)} accent="text-red-500" />
        <StatCard icon={<Percent className="h-5 w-5" />} label="Accuracy" value={`${result.accuracy}%`} accent="text-[var(--brand)]" />
      </div>

      {duration && (
        <div className="flex items-center gap-2 text-sm text-[var(--text-secondary)]">
          <Clock className="h-4 w-4" />
          Completed in {duration}
        </div>
      )}

      {/* performance by question type */}
      <ResultBreakdown breakdown={result.breakdown} />

      {/* per-question review */}
      <div>
        <h2 className="mb-4 text-lg font-semibold text-slate-900">Answer review</h2>
        <div className="space-y-4">
          {result.answers.map((a, idx) => (
            <Card
              key={a.question_id}
              className={`border-l-4 p-5 ${a.is_correct ? "border-l-green-500" : "border-l-red-500"}`}
            >
              <div className="mb-3 flex items-start justify-between gap-3">
                <p className="font-medium text-slate-900">
                  {idx + 1}. {a.text}
                </p>
                <span className="flex shrink-0 items-center gap-2">
                  {a.marked_for_review && (
                    <span className="inline-flex items-center gap-1 rounded-full bg-amber-50 px-2 py-0.5 text-xs font-semibold text-amber-600">
                      <Flag className="h-3 w-3" /> Marked
                    </span>
                  )}
                  {a.is_correct ? (
                    <CheckCircle2 className="h-5 w-5 text-green-500" />
                  ) : (
                    <XCircle className="h-5 w-5 text-red-500" />
                  )}
                </span>
              </div>
              <p className="text-sm text-slate-600">
                Your answer:{" "}
                <span className={`font-medium ${a.is_correct ? "text-green-700" : "text-red-700"}`}>
                  {a.user_answer ?? "— (no answer)"}
                </span>
              </p>
              {!a.is_correct && (
                <p className="mt-1 text-sm text-slate-600">
                  Correct answer: <span className="font-medium text-green-700">{a.correct_answer}</span>
                </p>
              )}
            </Card>
          ))}
        </div>
      </div>

      <div className="flex flex-wrap gap-3">
        <LinkButton href="/">Back to dashboard</LinkButton>
        <LinkButton href={`/test/${result.test_id}`} variant="secondary">
          Retake test
        </LinkButton>
      </div>
    </div>
  );
}

function StatCard({
  icon,
  label,
  value,
  accent = "text-[var(--text-secondary)]",
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
  accent?: string;
}) {
  return (
    <Card className="p-5">
      <div className="flex items-center justify-between">
        <p className="text-sm font-medium text-[var(--text-secondary)]">{label}</p>
        <span className={accent}>{icon}</span>
      </div>
      <p className="mt-2 text-3xl font-extrabold tracking-tight text-[var(--text-primary)]">{value}</p>
    </Card>
  );
}
