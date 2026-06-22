"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import { api, TestDetail, AnswerValue } from "@/lib/api";
import { useRequireAuth } from "@/hooks/useRequireAuth";
import { Card } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Skeleton } from "@/components/ui/Skeleton";
import { QuestionInput } from "@/components/QuestionInput";

function formatTime(seconds: number): string {
  const m = Math.floor(seconds / 60)
    .toString()
    .padStart(2, "0");
  const s = (seconds % 60).toString().padStart(2, "0");
  return `${m}:${s}`;
}

function isAnswered(v: AnswerValue): boolean {
  if (Array.isArray(v)) return v.length > 0;
  return typeof v === "string" && v.trim() !== "";
}

export default function TestPage() {
  const { token, ready } = useRequireAuth();
  const params = useParams();
  const router = useRouter();
  const testId = Number(params.id);

  const [test, setTest] = useState<TestDetail | null>(null);
  const [answers, setAnswers] = useState<Record<number, AnswerValue>>({});
  const [timeLeft, setTimeLeft] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const allQuestions = test
    ? test.sections.flatMap((s) => s.questions)
    : [];

  const handleSubmit = useCallback(async () => {
    if (!test || submitting) return;
    setSubmitting(true);
    try {
      const payload = test.sections
        .flatMap((s) => s.questions)
        .map((q) => ({ question_id: q.id, answer: answers[q.id] ?? null }));
      const result = await api.submit(test.id, payload);
      router.push(`/result/${result.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Submit failed");
      setSubmitting(false);
    }
  }, [test, answers, submitting, router]);

  useEffect(() => {
    if (!token) return;
    api
      .getTest(testId)
      .then((data) => {
        setTest(data);
        setTimeLeft(data.duration_minutes * 60);
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [token, testId]);

  useEffect(() => {
    if (timeLeft === null) return;
    if (timeLeft <= 0) {
      handleSubmit();
      return;
    }
    const timer = setTimeout(() => setTimeLeft((t) => (t ?? 0) - 1), 1000);
    return () => clearTimeout(timer);
  }, [timeLeft, handleSubmit]);

  if (!ready || !token) return null;
  if (loading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-16 w-full" />
        <Skeleton className="h-32 w-full" />
        <Skeleton className="h-40 w-full" />
      </div>
    );
  }
  if (error) {
    return (
      <p className="rounded-xl bg-red-50 px-4 py-3 text-sm text-red-600">{error}</p>
    );
  }
  if (!test) return null;

  const answeredCount = allQuestions.filter((q) => isAnswered(answers[q.id])).length;
  const progress = Math.round((answeredCount / allQuestions.length) * 100);
  const lowTime = timeLeft !== null && timeLeft < 60;

  let questionNumber = 0;

  return (
    <div>
      <div className="sticky top-[57px] z-20 mb-6">
        <Card className="px-4 py-3">
          <div className="flex items-center justify-between gap-4">
            <div className="min-w-0">
              <div className="flex items-center gap-2">
                <Badge tone={test.test_type === "reading" ? "blue" : "violet"}>
                  {test.test_type}
                </Badge>
                <h1 className="truncate text-base font-bold text-slate-900">
                  {test.title}
                </h1>
              </div>
              <p className="mt-0.5 text-sm text-slate-500">
                {answeredCount} / {allQuestions.length} answered
              </p>
            </div>
            {timeLeft !== null && (
              <div
                className={`shrink-0 rounded-xl px-3 py-1.5 font-mono text-lg font-semibold ${
                  lowTime
                    ? "animate-pulse bg-red-100 text-red-700"
                    : "bg-slate-100 text-slate-700"
                }`}
              >
                {formatTime(timeLeft)}
              </div>
            )}
          </div>
          <div className="mt-3 h-1.5 w-full overflow-hidden rounded-full bg-slate-100">
            <div
              className="h-full rounded-full bg-blue-600 transition-all"
              style={{ width: `${progress}%` }}
            />
          </div>
        </Card>
      </div>

      <div className="space-y-8">
        {test.sections.map((section) => (
          <section key={section.id} className="space-y-4">
            <div>
              <h2 className="text-lg font-bold text-slate-900">{section.title}</h2>
              {section.instructions && (
                <p className="mt-1 text-sm text-slate-500">{section.instructions}</p>
              )}
            </div>

            {section.passage && (
              <Card className="p-6">
                <h3 className="mb-3 text-sm font-semibold uppercase tracking-wide text-slate-400">
                  Passage
                </h3>
                <p className="whitespace-pre-line leading-relaxed text-slate-700">
                  {section.passage}
                </p>
              </Card>
            )}

            {section.audio_url && (
              <Card className="p-6">
                <h3 className="mb-3 text-sm font-semibold uppercase tracking-wide text-slate-400">
                  Audio
                </h3>
                <audio controls src={section.audio_url} className="w-full">
                  Your browser does not support audio.
                </audio>
              </Card>
            )}

            {section.questions.map((q) => {
              questionNumber += 1;
              return (
                <Card key={q.id} className="p-6">
                  <p className="mb-4 font-medium text-slate-900">
                    <span className="mr-2 inline-flex h-6 w-6 items-center justify-center rounded-full bg-blue-50 text-sm font-semibold text-blue-700">
                      {questionNumber}
                    </span>
                    {q.text}
                  </p>
                  <QuestionInput
                    question={q}
                    value={answers[q.id] ?? null}
                    onChange={(v) =>
                      setAnswers((prev) => ({ ...prev, [q.id]: v }))
                    }
                  />
                </Card>
              );
            })}
          </section>
        ))}
      </div>

      <Button
        onClick={handleSubmit}
        disabled={submitting}
        size="lg"
        className="mt-6 w-full py-3"
      >
        {submitting ? "Submitting..." : "Submit answers"}
      </Button>
    </div>
  );
}
