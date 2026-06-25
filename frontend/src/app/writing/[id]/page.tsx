"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { Brain, CheckCircle2, Loader2, Sparkles } from "lucide-react";
import { api, WritingTask } from "@/lib/api";
import { useRequireAuth } from "@/hooks/useRequireAuth";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Skeleton } from "@/components/ui/Skeleton";

function countWords(text: string): number {
  return text.match(/\b[\w'-]+\b/g)?.length ?? 0;
}

function formatTime(seconds: number): string {
  const m = Math.floor(seconds / 60)
    .toString()
    .padStart(2, "0");
  const s = (seconds % 60).toString().padStart(2, "0");
  return `${m}:${s}`;
}

function taskTone(taskType: number) {
  return taskType === 1 ? "blue" : "violet";
}

const REVIEW_STEPS = [
  "Reading your response",
  "Checking IELTS criteria",
  "Building your improvement plan",
];

export default function WritingTaskPage() {
  const { token, ready } = useRequireAuth();
  const params = useParams();
  const router = useRouter();
  const taskId = Number(params.id);

  const [task, setTask] = useState<WritingTask | null>(null);
  const [answer, setAnswer] = useState("");
  const [timeLeft, setTimeLeft] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (!token) return;
    api
      .getWritingTask(taskId)
      .then((data) => {
        setTask(data);
        setTimeLeft(data.duration_minutes * 60);
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [token, taskId]);

  useEffect(() => {
    if (timeLeft === null || timeLeft <= 0 || submitting) return;
    const timer = setTimeout(() => {
      setTimeLeft((seconds) => (seconds === null ? null : Math.max(seconds - 1, 0)));
    }, 1000);
    return () => clearTimeout(timer);
  }, [timeLeft, submitting]);

  const wordCount = countWords(answer);
  const meetsMinimum = task ? wordCount >= task.min_words : false;
  const lowTime = timeLeft !== null && timeLeft < 60;

  const handleSubmit = async () => {
    if (!task || submitting || answer.trim() === "") return;
    setSubmitting(true);
    setError("");
    try {
      const submission = await api.submitWriting(task.id, answer.trim());
      router.push(`/writing/result/${submission.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Submit failed");
      setSubmitting(false);
    }
  };

  if (!ready || !token) return null;
  if (loading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-16 w-full" />
        <Skeleton className="h-36 w-full" />
        <Skeleton className="h-72 w-full" />
      </div>
    );
  }
  if (!task && error) {
    return (
      <p className="rounded-xl bg-red-50 px-4 py-3 text-sm text-red-600">{error}</p>
    );
  }
  if (!task) return null;

  return (
    <div className="space-y-6">
      <div className="sticky top-[57px] z-20">
        <Card className="px-4 py-3">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div className="min-w-0">
              <div className="flex items-center gap-2">
                <Badge tone={taskTone(task.task_type)}>Task {task.task_type}</Badge>
                <h1 className="truncate text-base font-bold text-slate-900">
                  {task.title}
                </h1>
              </div>
              <p className="mt-0.5 text-sm text-slate-500">
                {wordCount} / {task.min_words} words
              </p>
            </div>
            <div className="flex items-center gap-2">
              <span
                className={`rounded-xl px-3 py-1.5 text-sm font-semibold ${
                  meetsMinimum
                    ? "bg-green-50 text-green-700"
                    : "bg-amber-50 text-amber-700"
                }`}
              >
                {meetsMinimum ? "Minimum reached" : "Keep writing"}
              </span>
              {timeLeft !== null && (
                <span
                  className={`rounded-xl px-3 py-1.5 font-mono text-lg font-semibold ${
                    lowTime
                      ? "animate-pulse bg-red-100 text-red-700"
                      : "bg-slate-100 text-slate-700"
                  }`}
                >
                  {formatTime(timeLeft)}
                </span>
              )}
            </div>
          </div>
          <div className="mt-3 h-1.5 w-full overflow-hidden rounded-full bg-slate-100">
            <div
              className={`h-full rounded-full transition-all ${
                meetsMinimum ? "bg-green-500" : "bg-blue-600"
              }`}
              style={{ width: `${Math.min((wordCount / task.min_words) * 100, 100)}%` }}
            />
          </div>
        </Card>
      </div>

      {error && (
        <p className="rounded-xl bg-red-50 px-4 py-3 text-sm text-red-600">{error}</p>
      )}

      <Card className="p-6">
        <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-slate-400">
          Prompt
        </h2>
        <p className="whitespace-pre-line leading-relaxed text-slate-700">
          {task.prompt}
        </p>
        {task.image_url && (
          <div
            aria-label="Writing task visual"
            role="img"
            className="mt-5 h-80 w-full rounded-xl bg-slate-50 bg-contain bg-center bg-no-repeat"
            style={{ backgroundImage: `url(${task.image_url})` }}
          />
        )}
      </Card>

      <Card className="p-6">
        <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
          <label htmlFor="writing-answer" className="font-semibold text-slate-900">
            Your answer
          </label>
          <span
            className={`text-sm font-medium ${
              meetsMinimum ? "text-green-600" : "text-slate-500"
            }`}
          >
            {wordCount} words
          </span>
        </div>
        <textarea
          id="writing-answer"
          value={answer}
          onChange={(e) => setAnswer(e.target.value)}
          placeholder="Write your response here..."
          disabled={submitting}
          className="min-h-80 w-full resize-y rounded-xl border border-slate-300 bg-white px-4 py-3 leading-relaxed text-slate-900 outline-none transition placeholder:text-slate-400 focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20"
        />
        <div className="mt-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <p className="text-sm text-slate-500">
            Aim for at least {task.min_words} words before submitting.
          </p>
          <Button
            onClick={handleSubmit}
            disabled={submitting || answer.trim() === ""}
            size="lg"
            className="sm:min-w-36"
          >
            {submitting ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                Reviewing
              </>
            ) : (
              "Submit"
            )}
          </Button>
        </div>
      </Card>

      {submitting && <AiReviewStatus />}
    </div>
  );
}

function AiReviewStatus() {
  return (
    <div className="fixed inset-x-0 bottom-0 z-50 px-4 pb-4 sm:px-6">
      <div className="mx-auto max-w-3xl overflow-hidden rounded-2xl border border-blue-100 bg-white/95 shadow-2xl shadow-slate-900/15 backdrop-blur">
        <div className="h-1 w-full overflow-hidden bg-slate-100">
          <div className="h-full w-2/3 animate-[aiReviewProgress_2.8s_ease-in-out_infinite] bg-blue-600" />
        </div>
        <div className="p-4 sm:p-5">
          <div className="flex items-start gap-4">
            <div className="relative flex h-11 w-11 flex-shrink-0 items-center justify-center rounded-xl bg-blue-600 text-white">
              <Brain className="h-5 w-5" />
              <span className="absolute inset-0 rounded-xl bg-blue-400/40 animate-ping" />
            </div>
            <div className="min-w-0 flex-1">
              <div className="flex flex-wrap items-center gap-2">
                <p className="font-semibold text-slate-950">AI examiner is reviewing</p>
                <span className="inline-flex items-center gap-1 rounded-full bg-blue-50 px-2 py-1 text-xs font-medium text-blue-700">
                  <Sparkles className="h-3.5 w-3.5" />
                  Usually under a minute
                </span>
              </div>
              <p className="mt-1 text-sm leading-relaxed text-slate-600">
                Keep this page open while your band score, criterion notes, and coach plan are prepared.
              </p>
              <div className="mt-4 grid gap-2 sm:grid-cols-3">
                {REVIEW_STEPS.map((step, index) => (
                  <div
                    key={step}
                    className="flex items-center gap-2 rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-700"
                  >
                    {index === 0 ? (
                      <CheckCircle2 className="h-4 w-4 flex-shrink-0 text-emerald-500" />
                    ) : (
                      <span className="h-2.5 w-2.5 flex-shrink-0 rounded-full bg-blue-500/70 animate-pulse" />
                    )}
                    <span className="truncate">{step}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
