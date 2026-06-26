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
  {
    title: "Reading your response",
    detail: "Checking whether this is a complete English IELTS answer.",
  },
  {
    title: "Applying IELTS criteria",
    detail: "Task response, coherence, vocabulary, and grammar are reviewed separately.",
  },
  {
    title: "Comparing band boundaries",
    detail: "Borderline 6.5-7.5 responses get a stricter second look.",
  },
  {
    title: "Preparing your coach plan",
    detail: "The final feedback turns examiner notes into practical next steps.",
  },
];
const REVIEW_CRITERIA = [
  "Task Response",
  "Coherence",
  "Lexical Resource",
  "Grammar",
];
const MIN_REVIEW_DISPLAY_MS = 8500;

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
      const startedAt = Date.now();
      const submission = await api.submitWriting(task.id, answer.trim());
      const elapsed = Date.now() - startedAt;
      if (elapsed < MIN_REVIEW_DISPLAY_MS) {
        await new Promise((resolve) => {
          window.setTimeout(resolve, MIN_REVIEW_DISPLAY_MS - elapsed);
        });
      }
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
  const [activeStep, setActiveStep] = useState(0);

  useEffect(() => {
    const timer = window.setInterval(() => {
      setActiveStep((step) => (step + 1) % REVIEW_STEPS.length);
    }, 2600);
    return () => window.clearInterval(timer);
  }, []);

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center overflow-y-auto bg-slate-950/80 px-4 py-6 backdrop-blur-md"
      role="status"
      aria-live="polite"
      aria-label="AI examiner is reviewing your writing"
    >
      <div className="fixed inset-x-0 top-0 h-1.5 overflow-hidden bg-slate-800">
        <div className="h-full w-1/2 animate-[aiReviewProgress_12s_ease-in-out_infinite] bg-blue-400" />
      </div>

      <div className="relative w-full max-w-6xl overflow-hidden rounded-2xl border border-slate-700 bg-white shadow-2xl shadow-slate-950/40">
        <div className="grid min-h-[min(760px,calc(100vh-3rem))] lg:grid-cols-[1.05fr_0.95fr]">
          <div className="relative flex items-center justify-center overflow-hidden bg-slate-950 p-6 text-white sm:p-8">
            <div className="absolute inset-0 opacity-40 [background-image:linear-gradient(rgba(148,163,184,0.16)_1px,transparent_1px),linear-gradient(90deg,rgba(148,163,184,0.16)_1px,transparent_1px)] [background-size:42px_42px]" />
            <div className="relative flex w-full max-w-xl flex-col items-center">
              <div className="relative flex h-72 w-72 items-center justify-center sm:h-96 sm:w-96">
                <div className="absolute inset-0 rounded-full border border-blue-300/20 animate-[spin_28s_linear_infinite]" />
                <div className="absolute inset-8 rounded-full border border-dashed border-emerald-300/30 animate-[spin_18s_linear_infinite_reverse]" />
                <div className="absolute inset-16 rounded-full border border-white/10 animate-[aiReviewGlow_2.8s_ease-in-out_infinite]" />

                <div className="relative h-64 w-52 overflow-hidden rounded-2xl border border-slate-200 bg-white p-5 text-slate-950 shadow-2xl shadow-blue-950/40 sm:h-80 sm:w-64 sm:p-6 animate-[aiReviewFloat_5s_ease-in-out_infinite]">
                  <div className="flex items-center justify-between border-b border-slate-200 pb-4">
                    <div>
                      <p className="text-[10px] font-semibold uppercase tracking-[0.22em] text-blue-600">
                        IELTS
                      </p>
                      <p className="mt-1 text-sm font-bold text-slate-950">
                        Writing script
                      </p>
                    </div>
                    <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-blue-600 text-white">
                      <Brain className="h-5 w-5" />
                    </div>
                  </div>

                  <div className="mt-5 space-y-3">
                    {[92, 78, 86, 64, 88, 72, 94, 58].map((width, index) => (
                      <div key={index} className="space-y-1.5">
                        <div
                          className="h-2 rounded-full bg-slate-200"
                          style={{ width: `${width}%` }}
                        />
                        {index === 2 || index === 5 ? (
                          <div className="h-2 w-2/3 rounded-full bg-slate-100" />
                        ) : null}
                      </div>
                    ))}
                  </div>

                  <div className="absolute inset-x-0 top-0 h-28 animate-[aiReviewScan_2.4s_ease-in-out_infinite] bg-gradient-to-b from-transparent via-blue-400/30 to-transparent" />
                  <div className="absolute inset-x-5 top-0 h-px animate-[aiReviewScan_2.4s_ease-in-out_infinite] bg-blue-500 shadow-[0_0_18px_rgba(37,99,235,0.8)]" />
                </div>

                <div className="absolute -right-2 bottom-10 rounded-2xl border border-emerald-300/30 bg-emerald-400/15 px-4 py-3 text-left shadow-xl backdrop-blur">
                  <p className="text-xs font-semibold text-emerald-100">
                    Examiner mode
                  </p>
                  <div className="mt-2 flex items-center gap-2 text-sm font-bold text-white">
                    <span className="h-2 w-2 rounded-full bg-emerald-300 animate-pulse" />
                    Reviewing
                  </div>
                </div>
              </div>

              <p className="mt-4 text-center text-sm leading-6 text-slate-300">
                Your essay is being checked against IELTS Writing criteria.
              </p>
            </div>
          </div>

          <div className="flex flex-col justify-center p-6 sm:p-8 lg:p-10">
            <div className="flex flex-wrap items-center gap-2">
              <span className="inline-flex items-center gap-1.5 rounded-full bg-blue-50 px-3 py-1.5 text-xs font-semibold text-blue-700">
                <Sparkles className="h-3.5 w-3.5" />
                AI review in progress
              </span>
              <span className="rounded-full bg-slate-100 px-3 py-1.5 text-xs font-medium text-slate-600">
                Usually under a minute
              </span>
            </div>

            <h2 className="mt-5 text-3xl font-bold leading-tight text-slate-950 sm:text-4xl">
              AI examiner is reviewing your essay
            </h2>
            <p className="mt-4 max-w-xl text-sm leading-6 text-slate-600 sm:text-base">
              Keep this page open while the system checks your response, applies IELTS criteria, and prepares your coach plan.
            </p>

            <div className="mt-8 rounded-2xl border border-slate-200 bg-slate-50 p-5">
              <div className="flex items-start gap-4">
                <div className="flex h-11 w-11 flex-shrink-0 items-center justify-center rounded-xl bg-blue-600 text-white shadow-lg shadow-blue-600/20">
                  <Loader2 className="h-5 w-5 animate-spin" />
                </div>
                <div>
                  <p className="font-semibold text-slate-950">
                    {REVIEW_STEPS[activeStep].title}
                  </p>
                  <p className="mt-1 text-sm leading-6 text-slate-600">
                    {REVIEW_STEPS[activeStep].detail}
                  </p>
                </div>
              </div>
            </div>

            <div className="mt-6 grid gap-3 sm:grid-cols-2">
              {REVIEW_CRITERIA.map((criterion, index) => {
                const active = index === activeStep % REVIEW_CRITERIA.length;
                const complete = index < activeStep % REVIEW_CRITERIA.length;
                return (
                  <div
                    key={criterion}
                    className={`rounded-xl border px-4 py-3 transition ${
                      active
                        ? "border-blue-300 bg-blue-50 shadow-sm shadow-blue-600/10"
                        : complete
                          ? "border-emerald-200 bg-emerald-50"
                          : "border-slate-200 bg-white"
                    }`}
                  >
                    <div className="flex items-center justify-between gap-3">
                      <p
                        className={`text-sm font-semibold ${
                          active ? "text-blue-800" : "text-slate-700"
                        }`}
                      >
                        {criterion}
                      </p>
                      {complete ? (
                        <CheckCircle2 className="h-4 w-4 flex-shrink-0 text-emerald-600" />
                      ) : (
                        <span
                          className={`h-2.5 w-2.5 flex-shrink-0 rounded-full ${
                            active ? "bg-blue-600 animate-pulse" : "bg-slate-300"
                          }`}
                        />
                      )}
                    </div>
                  </div>
                );
              })}
            </div>

            <div className="mt-8 space-y-3">
              {REVIEW_STEPS.map((step, index) => {
                const complete = index < activeStep;
                const active = index === activeStep;
                return (
                  <div key={step.title} className="flex items-start gap-3">
                    <div
                      className={`mt-0.5 flex h-6 w-6 flex-shrink-0 items-center justify-center rounded-full border ${
                        active
                          ? "border-blue-600 bg-blue-600 text-white"
                          : complete
                            ? "border-emerald-500 bg-emerald-500 text-white"
                            : "border-slate-300 bg-white text-slate-400"
                      }`}
                    >
                      {complete ? (
                        <CheckCircle2 className="h-4 w-4" />
                      ) : active ? (
                        <Loader2 className="h-3.5 w-3.5 animate-spin" />
                      ) : (
                        <span className="h-1.5 w-1.5 rounded-full bg-current" />
                      )}
                    </div>
                    <div className="min-w-0">
                      <p
                        className={`text-sm font-semibold ${
                          active ? "text-slate-950" : "text-slate-600"
                        }`}
                      >
                        {step.title}
                      </p>
                      <p className="text-xs leading-5 text-slate-500">{step.detail}</p>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
