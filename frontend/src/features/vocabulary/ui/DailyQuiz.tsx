"use client";

import { useCallback, useEffect, useState } from "react";
import { CheckCircle2, RotateCcw, XCircle } from "lucide-react";
import { api, type DailyQuiz as DailyQuizData, type QuizResult } from "@/shared/api";
import { Button, Card, Skeleton } from "@/shared/ui";

export function DailyQuiz() {
  const [quiz, setQuiz] = useState<DailyQuizData | null>(null);
  const [answers, setAnswers] = useState<(number | null)[]>([]);
  const [result, setResult] = useState<QuizResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const q = await api.getDailyQuiz();
      setQuiz(q);
      setAnswers(new Array(q.questions.length).fill(null));
      setResult(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load today's quiz");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    const t = window.setTimeout(() => void load(), 0);
    return () => window.clearTimeout(t);
  }, [load]);

  const submit = async () => {
    setSubmitting(true);
    setError("");
    try {
      setResult(await api.submitDailyQuiz(answers));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not submit your answers");
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <Card className="p-6">
        <Skeleton className="h-40 w-full" />
      </Card>
    );
  }

  if (!quiz || quiz.questions.length === 0) {
    return (
      <Card className="p-6 text-center">
        <p className="font-semibold text-slate-800">No practice yet</p>
        <p className="mx-auto mt-1 max-w-md text-sm text-slate-500">
          Save a few words while reading, mark them <strong>Train</strong>, and a
          personalised quiz appears here each day.
        </p>
      </Card>
    );
  }

  const allAnswered = answers.every((a) => a !== null);

  return (
    <Card className="p-6">
      <div className="flex items-center justify-between gap-4">
        <div>
          <p className="text-sm font-semibold text-[var(--brand)]">Today&apos;s practice</p>
          <h2 className="mt-0.5 text-lg font-bold text-slate-950">Vocabulary quiz</h2>
        </div>
        {result ? (
          <div className="text-right">
            <p className="text-2xl font-extrabold text-slate-950">
              {result.score}/{result.total}
            </p>
            <p className="text-xs text-slate-400">correct</p>
          </div>
        ) : quiz.completed ? (
          <span className="rounded-md bg-emerald-50 px-2.5 py-1 text-xs font-semibold text-emerald-700">
            Done today · {quiz.score}/{quiz.total}
          </span>
        ) : null}
      </div>

      {error && (
        <p className="mt-3 rounded-xl bg-red-50 px-4 py-3 text-sm text-red-700">{error}</p>
      )}

      <div className="mt-5 space-y-6">
        {quiz.questions.map((q, qi) => {
          const res = result?.results[qi];
          return (
            <div key={qi}>
              <p className="whitespace-pre-line text-sm font-semibold text-slate-800">
                {qi + 1}. {q.prompt}
              </p>
              <div className="mt-2 grid gap-2 sm:grid-cols-2">
                {q.options.map((opt, oi) => {
                  const chosen = answers[qi] === oi;
                  let tone = chosen
                    ? "border-[var(--brand)] bg-[var(--brand)]/[0.06] text-slate-900"
                    : "border-slate-200 text-slate-600 hover:border-slate-300";
                  if (res) {
                    if (oi === res.answer_index)
                      tone = "border-emerald-300 bg-emerald-50 text-emerald-800";
                    else if (chosen) tone = "border-red-300 bg-red-50 text-red-800";
                    else tone = "border-slate-200 text-slate-400";
                  }
                  return (
                    <button
                      key={oi}
                      type="button"
                      disabled={!!result}
                      onClick={() =>
                        setAnswers((a) => a.map((v, i) => (i === qi ? oi : v)))
                      }
                      className={`rounded-xl border px-3 py-2 text-left text-sm font-medium transition disabled:cursor-default ${tone}`}
                    >
                      {opt}
                    </button>
                  );
                })}
              </div>
              {res && (
                <p
                  className={`mt-2 flex items-start gap-1.5 text-xs ${
                    res.correct ? "text-emerald-700" : "text-red-700"
                  }`}
                >
                  {res.correct ? (
                    <CheckCircle2 className="mt-0.5 h-3.5 w-3.5 shrink-0" />
                  ) : (
                    <XCircle className="mt-0.5 h-3.5 w-3.5 shrink-0" />
                  )}
                  <span>{res.explanation}</span>
                </p>
              )}
            </div>
          );
        })}
      </div>

      <div className="mt-6 flex flex-wrap items-center gap-3">
        {!result ? (
          <Button onClick={submit} disabled={!allAnswered || submitting}>
            {submitting ? "Checking…" : "Check answers"}
          </Button>
        ) : (
          <Button variant="secondary" onClick={() => void load()}>
            <RotateCcw className="h-4 w-4" /> Try again
          </Button>
        )}
        {!result && !allAnswered && (
          <span className="text-xs text-slate-400">
            Answer all {quiz.questions.length} questions to check.
          </span>
        )}
      </div>
    </Card>
  );
}
