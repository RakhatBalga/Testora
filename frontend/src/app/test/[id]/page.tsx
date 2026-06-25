"use client";

import { useEffect, useMemo, useState, useCallback, useRef } from "react";
import { useParams, useRouter } from "next/navigation";
import { ChevronLeft, ChevronRight, Flag, Clock, ListChecks } from "lucide-react";
import { api, TestDetail, AnswerValue, Section } from "@/lib/api";
import { useRequireAuth } from "@/hooks/useRequireAuth";
import { Card } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Skeleton } from "@/components/ui/Skeleton";
import { QuestionInput } from "@/components/QuestionInput";
import { QuestionPalette, type PaletteItem } from "@/components/test/QuestionPalette";
import { ReviewModal } from "@/components/test/ReviewModal";

type FlatItem = {
  id: number;
  number: number;
  section: Section;
};

function formatTime(seconds: number): string {
  const m = Math.floor(seconds / 60).toString().padStart(2, "0");
  const s = (seconds % 60).toString().padStart(2, "0");
  return `${m}:${s}`;
}

function isAnswered(v: AnswerValue | undefined): boolean {
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
  const [marked, setMarked] = useState<Record<number, boolean>>({});
  const [currentId, setCurrentId] = useState<number | null>(null);
  const [timeLeft, setTimeLeft] = useState<number | null>(null);
  const [reviewOpen, setReviewOpen] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const storeKey = `testora-test-${testId}`;
  const submittedRef = useRef(false);

  const flat: FlatItem[] = useMemo(() => {
    if (!test) return [];
    const items: FlatItem[] = [];
    let n = 0;
    for (const section of test.sections) {
      for (const q of section.questions) {
        n += 1;
        items.push({ id: q.id, number: n, section });
      }
    }
    return items;
  }, [test]);

  const handleSubmit = useCallback(async () => {
    if (!test || submittedRef.current) return;
    submittedRef.current = true;
    setSubmitting(true);
    try {
      const payload = flat.map((it) => ({
        question_id: it.id,
        answer: answers[it.id] ?? null,
        marked_for_review: !!marked[it.id],
      }));
      const elapsed = Math.max(0, test.duration_minutes * 60 - (timeLeft ?? 0));
      const result = await api.submit(test.id, payload, elapsed);
      localStorage.removeItem(`${storeKey}-answers`);
      localStorage.removeItem(`${storeKey}-marked`);
      localStorage.removeItem(`${storeKey}-deadline`);
      router.push(`/result/${result.id}`);
    } catch (err) {
      submittedRef.current = false;
      setSubmitting(false);
      setError(err instanceof Error ? err.message : "Submit failed");
    }
  }, [test, flat, answers, marked, timeLeft, router, storeKey]);

  // Load test + restore saved progress and a persistent deadline.
  useEffect(() => {
    if (!token) return;
    api
      .getTest(testId)
      .then((data) => {
        setTest(data);
        const firstId = data.sections.flatMap((s) => s.questions)[0]?.id ?? null;
        setCurrentId(firstId);

        try {
          const savedAnswers = localStorage.getItem(`${storeKey}-answers`);
          const savedMarked = localStorage.getItem(`${storeKey}-marked`);
          if (savedAnswers) setAnswers(JSON.parse(savedAnswers));
          if (savedMarked) setMarked(JSON.parse(savedMarked));
        } catch {
          /* ignore corrupt storage */
        }

        const savedDeadline = Number(localStorage.getItem(`${storeKey}-deadline`));
        const now = Date.now();
        if (savedDeadline && savedDeadline > now) {
          setTimeLeft(Math.round((savedDeadline - now) / 1000));
        } else if (savedDeadline && savedDeadline <= now) {
          setTimeLeft(0);
        } else {
          const deadline = now + data.duration_minutes * 60 * 1000;
          localStorage.setItem(`${storeKey}-deadline`, String(deadline));
          setTimeLeft(data.duration_minutes * 60);
        }
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token, testId]);

  // Auto-save answers + marks.
  useEffect(() => {
    if (!test) return;
    localStorage.setItem(`${storeKey}-answers`, JSON.stringify(answers));
  }, [answers, test, storeKey]);
  useEffect(() => {
    if (!test) return;
    localStorage.setItem(`${storeKey}-marked`, JSON.stringify(marked));
  }, [marked, test, storeKey]);

  // Persistent countdown; auto-submit at zero.
  useEffect(() => {
    if (timeLeft === null) return;
    if (timeLeft <= 0) {
      const submitTimer = window.setTimeout(() => {
        void handleSubmit();
      }, 0);
      return () => window.clearTimeout(submitTimer);
    }
    const timer = setTimeout(() => setTimeLeft((t) => (t ?? 0) - 1), 1000);
    return () => clearTimeout(timer);
  }, [timeLeft, handleSubmit]);

  const paletteItems: PaletteItem[] = useMemo(
    () =>
      flat.map((it) => ({
        id: it.id,
        number: it.number,
        sectionTitle: it.section.title,
        answered: isAnswered(answers[it.id]),
        marked: !!marked[it.id],
      })),
    [flat, answers, marked]
  );

  if (!ready || !token) return null;
  if (loading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-16 w-full" />
        <Skeleton className="h-64 w-full" />
        <Skeleton className="h-24 w-full" />
      </div>
    );
  }
  if (error) {
    return <p className="rounded-xl bg-red-50 px-4 py-3 text-sm text-red-600">{error}</p>;
  }
  if (!test) return null;
  if (flat.length === 0) {
    return <Card className="p-8 text-center text-slate-500">This test has no questions yet.</Card>;
  }

  const currentIndex = flat.findIndex((it) => it.id === currentId);
  const current = flat[currentIndex] ?? flat[0];
  const section = current.section;
  const currentQuestion = section.questions.find((q) => q.id === current.id)!;
  const answeredCount = paletteItems.filter((i) => i.answered).length;
  const lowTime = timeLeft !== null && timeLeft < 60;
  const isMarked = !!marked[current.id];

  const goTo = (id: number) => setCurrentId(id);
  const goPrev = () => currentIndex > 0 && setCurrentId(flat[currentIndex - 1].id);
  const goNext = () => currentIndex < flat.length - 1 && setCurrentId(flat[currentIndex + 1].id);
  const toggleMark = () => setMarked((prev) => ({ ...prev, [current.id]: !prev[current.id] }));

  return (
    <div className="pb-24 lg:pb-0">
      {/* sticky exam header */}
      <div className="sticky top-[57px] z-20 mb-6">
        <Card className="px-4 py-3">
          <div className="flex items-center justify-between gap-4">
            <div className="min-w-0">
              <div className="flex items-center gap-2">
                <Badge tone={test.test_type === "reading" ? "blue" : "violet"}>{test.test_type}</Badge>
                <h1 className="truncate text-base font-bold text-slate-900">{test.title}</h1>
              </div>
              <p className="mt-0.5 text-sm text-slate-500">
                {answeredCount} / {flat.length} answered
              </p>
            </div>
            {timeLeft !== null && (
              <div
                className={`flex shrink-0 items-center gap-1.5 rounded-xl px-3 py-1.5 font-mono text-lg font-semibold ${
                  lowTime ? "animate-pulse bg-red-100 text-red-700" : "bg-slate-100 text-slate-700"
                }`}
              >
                <Clock className="h-4 w-4" />
                {formatTime(timeLeft)}
              </div>
            )}
          </div>
        </Card>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        {/* main column: passage/audio + current question */}
        <div className="space-y-4 lg:col-span-2">
          {section.passage && (
            <Card className="max-h-[60vh] overflow-y-auto p-6">
              <h3 className="mb-3 text-sm font-semibold uppercase tracking-wide text-slate-400">
                {section.title}
              </h3>
              <p className="whitespace-pre-line leading-relaxed text-slate-700">{section.passage}</p>
            </Card>
          )}

          {section.audio_url && (
            <Card className="p-6">
              <h3 className="mb-3 text-sm font-semibold uppercase tracking-wide text-slate-400">
                {section.title} — Audio
              </h3>
              <audio controls src={section.audio_url} className="w-full">
                Your browser does not support audio.
              </audio>
              {section.instructions && <p className="mt-3 text-sm text-slate-500">{section.instructions}</p>}
            </Card>
          )}

          <Card className="p-6">
            <div className="mb-4 flex items-start justify-between gap-3">
              <p className="font-medium text-slate-900">
                <span className="mr-2 inline-flex h-6 w-6 items-center justify-center rounded-full bg-blue-50 text-sm font-semibold text-blue-700">
                  {current.number}
                </span>
                {currentQuestion.text}
              </p>
              <button
                type="button"
                onClick={toggleMark}
                className={`inline-flex shrink-0 items-center gap-1.5 rounded-lg border px-2.5 py-1.5 text-xs font-semibold transition ${
                  isMarked
                    ? "border-amber-300 bg-amber-50 text-amber-600"
                    : "border-[var(--border)] text-slate-500 hover:bg-slate-50"
                }`}
              >
                <Flag className="h-3.5 w-3.5" />
                {isMarked ? "Marked" : "Mark"}
              </button>
            </div>

            <QuestionInput
              question={currentQuestion}
              value={answers[current.id] ?? null}
              onChange={(v) => setAnswers((prev) => ({ ...prev, [current.id]: v }))}
            />

            <div className="mt-6 flex items-center justify-between gap-3">
              <Button variant="secondary" onClick={goPrev} disabled={currentIndex === 0}>
                <ChevronLeft className="h-4 w-4" /> Previous
              </Button>
              {currentIndex < flat.length - 1 ? (
                <Button onClick={goNext}>
                  Next <ChevronRight className="h-4 w-4" />
                </Button>
              ) : (
                <Button onClick={() => setReviewOpen(true)}>Review &amp; submit</Button>
              )}
            </div>
          </Card>
        </div>

        {/* palette sidebar (desktop) */}
        <div className="hidden lg:block">
          <Card className="sticky top-[130px] p-5">
            <div className="mb-3 flex items-center justify-between">
              <h2 className="text-sm font-semibold text-[var(--text-primary)]">Questions</h2>
              <Button size="sm" onClick={() => setReviewOpen(true)}>
                <ListChecks className="h-4 w-4" /> Review
              </Button>
            </div>
            <QuestionPalette items={paletteItems} currentId={current.id} onJump={goTo} />
          </Card>
        </div>
      </div>

      {/* mobile bottom bar */}
      <div className="fixed inset-x-0 bottom-0 z-20 border-t border-[var(--border)] bg-white/95 p-3 backdrop-blur lg:hidden">
        <div className="mx-auto flex max-w-3xl items-center gap-2">
          <Button variant="secondary" onClick={goPrev} disabled={currentIndex === 0} className="px-3">
            <ChevronLeft className="h-4 w-4" />
          </Button>
          <Button onClick={() => setReviewOpen(true)} variant="secondary" className="flex-1">
            <ListChecks className="h-4 w-4" /> {answeredCount}/{flat.length} · Review
          </Button>
          <Button onClick={goNext} disabled={currentIndex === flat.length - 1} className="px-3">
            <ChevronRight className="h-4 w-4" />
          </Button>
        </div>
      </div>

      <ReviewModal
        open={reviewOpen || (timeLeft !== null && timeLeft <= 0)}
        items={paletteItems}
        currentId={current.id}
        submitting={submitting}
        timeUp={timeLeft !== null && timeLeft <= 0}
        onJump={goTo}
        onClose={() => setReviewOpen(false)}
        onSubmit={handleSubmit}
      />
    </div>
  );
}
