"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useParams } from "next/navigation";
import { BookOpen, ListChecks, Loader2 } from "lucide-react";
import {
  api,
  type AnswerValue,
  type AttemptResult,
  type TestDetail,
} from "@/lib/api";
import { useRequireAuth } from "@/hooks/useRequireAuth";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Skeleton } from "@/components/ui/Skeleton";
import { ReadingPassage } from "@/components/reading/ReadingPassage";
import { ReadingPassageNav } from "@/components/reading/ReadingPassageNav";
import { ReadingQuestions } from "@/components/reading/ReadingQuestions";
import { ReadingTimer } from "@/components/reading/ReadingTimer";
import { ReadingReviewSplit } from "@/components/reading/ReadingReviewSplit";
import { useReadingTimer } from "@/components/reading/useReadingTimer";
import {
  buildGroups,
  flattenQuestions,
  isAnswered,
  type AnswerMap,
} from "@/components/reading/types";

type Tab = "passage" | "questions";

export default function ReadingPage() {
  const { token, ready } = useRequireAuth();
  const params = useParams();
  const testId = Number(params.id);
  const storeKey = `reading-${testId}`;

  const [test, setTest] = useState<TestDetail | null>(null);
  const [answers, setAnswers] = useState<AnswerMap>({});
  const [activePassage, setActivePassage] = useState(0);
  const [activeNumber, setActiveNumber] = useState<number | null>(null);
  const [tab, setTab] = useState<Tab>("passage");
  const [result, setResult] = useState<AttemptResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  const passageScrollRef = useRef<HTMLDivElement>(null);
  const questionsScrollRef = useRef<HTMLDivElement>(null);
  const submittedRef = useRef(false);

  const groups = useMemo(() => (test ? buildGroups(test) : []), [test]);
  const flat = useMemo(() => flattenQuestions(groups), [groups]);
  const answeredCount = useMemo(
    () => flat.filter((q) => isAnswered(answers[q.id])).length,
    [flat, answers]
  );
  const group = groups[activePassage];

  const handleSubmit = useCallback(async () => {
    if (!test || submittedRef.current) return;
    submittedRef.current = true;
    setSubmitting(true);
    try {
      const payload = flat.map((q) => ({
        question_id: q.id,
        answer: answers[q.id] ?? null,
      }));
      const elapsed = Math.max(0, test.duration_minutes * 60 - (timerRef.current ?? 0));
      const res = await api.submit(test.id, payload, elapsed);
      localStorage.setItem(`${storeKey}-result`, String(res.id));
      localStorage.removeItem(`${storeKey}-answers`);
      localStorage.removeItem(`${storeKey}-updated`);
      clearTimer();
      setResult(res);
      window.scrollTo({ top: 0 });
    } catch (err) {
      submittedRef.current = false;
      setError(err instanceof Error ? err.message : "Submit failed");
    } finally {
      setSubmitting(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [test, flat, answers, storeKey]);

  const { remaining, paused, pause, resume, clear: clearTimer } = useReadingTimer(
    storeKey,
    (test?.duration_minutes ?? 60) * 60,
    handleSubmit
  );
  const timerRef = useRef<number | null>(null);
  timerRef.current = remaining;

  // Load test + restore answers + restore a prior submitted result.
  useEffect(() => {
    if (!token) return;
    let cancelled = false;
    (async () => {
      try {
        const data = await api.getTest(testId);
        if (cancelled) return;
        setTest(data);
        setActiveNumber(data.sections.flatMap((s) => s.questions).length ? 1 : null);

        try {
          const saved = localStorage.getItem(`${storeKey}-answers`);
          if (saved) setAnswers(JSON.parse(saved));
        } catch {
          /* ignore corrupt storage */
        }

        const savedResult = localStorage.getItem(`${storeKey}-result`);
        if (savedResult) {
          try {
            const attempt = await api.getAttempt(Number(savedResult));
            if (!cancelled) setResult(attempt);
          } catch {
            localStorage.removeItem(`${storeKey}-result`);
          }
        }
      } catch (err) {
        if (!cancelled) setError(err instanceof Error ? err.message : "Failed to load test");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token, testId]);

  // Autosave answers (no save button). Record a timestamp so the practice
  // library can show "last activity" for an unfinished attempt.
  useEffect(() => {
    if (!test || result) return;
    localStorage.setItem(`${storeKey}-answers`, JSON.stringify(answers));
    if (Object.keys(answers).length > 0) {
      localStorage.setItem(`${storeKey}-updated`, String(Date.now()));
    }
  }, [answers, test, result, storeKey]);

  const handleAnswer = useCallback((questionId: number, value: AnswerValue) => {
    setAnswers((prev) => ({ ...prev, [questionId]: value }));
  }, []);

  const selectPassage = useCallback(
    (index: number) => {
      if (index < 0 || index >= groups.length) return;
      setActivePassage(index);
      setActiveNumber(groups[index].start);
      setTab("passage");
      passageScrollRef.current?.scrollTo({ top: 0 });
      questionsScrollRef.current?.scrollTo({ top: 0 });
    },
    [groups]
  );

  const retake = useCallback(() => {
    localStorage.removeItem(`${storeKey}-result`);
    localStorage.removeItem(`${storeKey}-answers`);
    localStorage.removeItem(`${storeKey}-updated`);
    clearTimer();
    setResult(null);
    setAnswers({});
    submittedRef.current = false;
    window.location.reload();
  }, [storeKey, clearTimer]);

  if (!ready || !token) return null;

  if (loading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-16 w-full" />
        <div className="grid gap-6 lg:grid-cols-[65fr_35fr]">
          <Skeleton className="h-[70vh] w-full" />
          <Skeleton className="h-[70vh] w-full" />
        </div>
      </div>
    );
  }
  if (error) {
    return <p className="rounded-xl bg-red-50 px-4 py-3 text-sm text-red-600">{error}</p>;
  }
  if (!test || flat.length === 0 || !group) {
    return <Card className="p-8 text-center text-slate-500">This test has no questions yet.</Card>;
  }

  // ---- Review mode (split-screen with passage evidence highlighting) ----
  if (result) {
    return <ReadingReviewSplit result={result} groups={groups} onRetake={retake} />;
  }

  // ---- Exam mode: full-bleed 95vw breakout, bounded to the viewport so only
  // the passage/question panels scroll (the exam chrome stays fixed). ----
  return (
    <div className="relative left-1/2 flex h-[calc(100vh-8rem)] min-h-[480px] w-[95vw] max-w-[1600px] -translate-x-1/2 flex-col overflow-hidden">
      {/* Single compact exam header — title · passage tabs · progress · timer ·
          Submit on ONE row, so chrome above the passage stays ~48px. */}
      <div className="flex flex-shrink-0 items-center gap-3 pb-2">
        <h1 className="hidden min-w-0 max-w-[12rem] shrink truncate text-sm font-bold text-slate-900 xl:block">
          {test.title}
        </h1>
        <div className="min-w-0 flex-1">
          <ReadingPassageNav
            groups={groups}
            active={activePassage}
            answers={answers}
            onSelect={selectPassage}
          />
        </div>
        <span className="hidden flex-shrink-0 text-xs font-medium tabular-nums text-slate-500 sm:block">
          <strong className="text-slate-900">{answeredCount}</strong>/{flat.length}
        </span>
        <ReadingTimer remaining={remaining} paused={paused} onPause={pause} onResume={resume} />
        <Button onClick={handleSubmit} disabled={submitting}>
          {submitting ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <ListChecks className="h-4 w-4" />
          )}
          Submit
        </Button>
      </div>

      {/* Mobile/tablet tab switch */}
      <div className="mb-3 flex flex-shrink-0 gap-1 rounded-xl border border-[var(--border)] bg-slate-50 p-1 lg:hidden">
        {(["passage", "questions"] as Tab[]).map((t) => (
          <button
            key={t}
            type="button"
            onClick={() => setTab(t)}
            className={`flex flex-1 items-center justify-center gap-2 rounded-lg py-2 text-sm font-semibold capitalize transition ${
              tab === t ? "bg-white text-[var(--brand)] shadow-sm" : "text-slate-500"
            }`}
          >
            {t === "passage" ? <BookOpen className="h-4 w-4" /> : <ListChecks className="h-4 w-4" />}
            {t}
          </button>
        ))}
      </div>

      {/* Split: 60/40 on laptops (lg), 65/35 only on very large screens (2xl).
          Each column scrolls independently — grid-rows minmax(0,1fr) + min-h-0
          caps the row so children scroll internally instead of stretching. */}
      <div className="grid min-h-0 flex-1 grid-cols-1 grid-rows-[minmax(0,1fr)] gap-4 lg:grid-cols-[60fr_40fr] lg:gap-5 2xl:grid-cols-[65fr_35fr]">
        <div
          ref={passageScrollRef}
          className={`min-h-0 overflow-y-auto rounded-xl bg-white px-7 py-5 shadow-sm ring-1 ring-slate-100 sm:px-10 ${
            tab === "passage" ? "block" : "hidden"
          } lg:block`}
        >
          <ReadingPassage section={group.section} />
        </div>

        <div
          ref={questionsScrollRef}
          className={`min-h-0 overflow-y-auto rounded-xl bg-white p-3.5 shadow-sm ring-1 ring-slate-100 sm:p-4 ${
            tab === "questions" ? "block" : "hidden"
          } lg:block`}
        >
          <ReadingQuestions
            group={group}
            answers={answers}
            activeNumber={activeNumber}
            onAnswer={handleAnswer}
            onFocusQuestion={setActiveNumber}
          />
        </div>
      </div>
    </div>
  );
}
