"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { api, AttemptResult } from "@/lib/api";
import { useRequireAuth } from "@/hooks/useRequireAuth";
import { Card } from "@/components/ui/Card";
import { LinkButton } from "@/components/ui/Button";
import { Skeleton } from "@/components/ui/Skeleton";

export default function ResultPage() {
  const { token, ready } = useRequireAuth();
  const params = useParams();
  const attemptId = Number(params.id);

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
        <Skeleton className="h-40 w-full" />
        <Skeleton className="h-24 w-full" />
      </div>
    );
  }
  if (error) {
    return (
      <p className="rounded-xl bg-red-50 px-4 py-3 text-sm text-red-600">{error}</p>
    );
  }
  if (!result) return null;

  const percent = Math.round((result.score / result.total) * 100);
  const band = result.band;
  const bandTone =
    band === null
      ? "text-slate-400"
      : band >= 7
      ? "text-green-600"
      : band >= 5.5
      ? "text-amber-600"
      : "text-red-600";

  return (
    <div>
      <Card className="mb-8 overflow-hidden">
        <div className="bg-hero p-8 text-center">
          <p className="text-sm font-medium text-slate-500">{result.test_title}</p>
          {band !== null && (
            <>
              <p className="mt-4 text-xs font-semibold uppercase tracking-wide text-slate-400">
                Estimated IELTS band
              </p>
              <p className={`text-6xl font-extrabold ${bandTone}`}>
                {band.toFixed(1)}
              </p>
            </>
          )}
          <p className="mt-3 text-slate-500">
            {result.score} / {result.total} correct ({percent}%)
          </p>
        </div>
      </Card>

      <h2 className="mb-4 text-lg font-semibold text-slate-900">Review</h2>
      <div className="space-y-4">
        {result.answers.map((a, idx) => (
          <Card
            key={a.question_id}
            className={`border-l-4 p-5 ${
              a.is_correct ? "border-l-green-500" : "border-l-red-500"
            }`}
          >
            <p className="mb-3 font-medium text-slate-900">
              {idx + 1}. {a.text}
            </p>
            <p className="text-sm text-slate-600">
              Your answer:{" "}
              <span
                className={`font-medium ${
                  a.is_correct ? "text-green-700" : "text-red-700"
                }`}
              >
                {a.user_answer ?? "— (no answer)"}
              </span>
            </p>
            {!a.is_correct && (
              <p className="mt-1 text-sm text-slate-600">
                Correct answer:{" "}
                <span className="font-medium text-green-700">
                  {a.correct_answer}
                </span>
              </p>
            )}
          </Card>
        ))}
      </div>

      <div className="mt-8 flex flex-wrap gap-3">
        <LinkButton href="/">Back to tests</LinkButton>
        <LinkButton href="/profile" variant="secondary">
          My results
        </LinkButton>
      </div>
    </div>
  );
}
