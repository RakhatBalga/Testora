"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useParams } from "next/navigation";
import { ListChecks } from "lucide-react";
import {
  api,
  type AnswerValue,
  type AttemptResult,
  type TestDetail,
} from "@/shared/api";
import { useRequireAuth } from "@/shared/auth";
import { Card } from "@/shared/ui";
import { Button } from "@/shared/ui";
import { Skeleton } from "@/shared/ui";
import { ReadingTimer } from "@/features/reading-session";
import { ReadingProgress } from "@/features/reading-session";
import { ReadingReview } from "@/features/reading-session";
import { useReadingTimer } from "@/features/reading-session";
import {
  buildGroups,
  flattenQuestions,
  isAnswered,
  type AnswerMap,
} from "@/features/reading-session";
import { ListeningAudioPlayer } from "@/features/listening-session";
import { ListeningSectionNav } from "@/features/listening-session";
import { ListeningQuestions } from "@/features/listening-session";
import { SubmitConfirm } from "@/features/listening-session";

export default function ListeningPage() {
  const { token, ready } = useRequireAuth();
  const params = useParams();
  const testId = Number(params?.id);
  const storeKey = `listening-${testId}`;

  const [test, setTest] = useState<TestDetail | null>(null);
  const [answers, setAnswers] = useState<AnswerMap>({});
  const [activeSection, setActiveSection] = useState(0);
  const [activeNumber, setActiveNumber] = useState<number | null>(null);
  const [result, setResult] = useState<AttemptResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  const submittedRef = useRef(false);
  const remainingRef = useRef<number | null>(null);
  const clearTimerRef = useRef<(() => void) | null>(null);

  const sections = useMemo(() => (test ? buildGroups(test) : []), [test]);
  const flat = useMemo(() => flattenQuestions(sections), [sections]);
  const answeredCount = useMemo(
    () => flat.filter((q) => isAnswered(answers[q.id])).length,
    [flat, answers]
  );
  const section = sections[activeSection];

  const handleSubmit = useCallback(async () => {
    if (!test || submittedRef.current) return;
    submittedRef.current = true;
    setSubmitting(true);
    try {
      const payload = flat.map((q) => ({ question_id: q.id, answer: answers[q.id] ?? null }));
      const elapsed = Math.max(0, test.duration_minutes * 60 - (remainingRef.current ?? 0));
      const res = await api.submit(test.id, payload, elapsed);
      localStorage.setItem(`${storeKey}-result`, String(res.id));
      localStorage.removeItem(`${storeKey}-answers`);
      localStorage.removeItem(`${storeKey}-updated`);
      clearTimerRef.current?.();
      setConfirmOpen(false);
      setResult(res);
      window.scrollTo({ top: 0 });
    } catch (err) {
      submittedRef.current = false;
      setError(err instanceof Error ? err.message : "Submit failed");
    } finally {
      setSubmitting(false);
    }
  }, [test, flat, answers, storeKey]);

  const { remaining, paused, pause, resume, clear: clearTimer } = useReadingTimer(
    storeKey,
    (test?.duration_minutes ?? 30) * 60,
    handleSubmit // auto-submit on expiry (skips the confirm dialog)
  );

  useEffect(() => {
    remainingRef.current = remaining;
  }, [remaining]);

  useEffect(() => {
    clearTimerRef.current = clearTimer;
  }, [clearTimer]);

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
          /* ignore */
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

  const selectSection = useCallback(
    (index: number) => {
      if (index < 0 || index >= sections.length) return;
      setActiveSection(index);
      setActiveNumber(sections[index].start);
      window.scrollTo({ top: 0, behavior: "smooth" });
    },
    [sections]
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
        <Skeleton className="h-20 w-full" />
        <Skeleton className="h-[60vh] w-full" />
      </div>
    );
  }
  if (error) {
    return <p className="rounded-xl bg-red-50 px-4 py-3 text-sm text-red-600">{error}</p>;
  }
  if (!test || flat.length === 0 || !section) {
    return <Card className="p-8 text-center text-slate-500">This test has no questions yet.</Card>;
  }

  if (result) {
    return <ReadingReview result={result} groups={sections} onRetake={retake} />;
  }

  return (
    <div className="pb-12">
      {/* Sticky exam chrome: title/timer, audio, section nav */}
      <div className="sticky top-[57px] z-30 -mx-5 space-y-2 border-b border-[var(--border)] bg-[var(--background)]/95 px-5 pb-2 pt-2 backdrop-blur sm:-mx-8 sm:px-8">
        <div className="flex items-center justify-between gap-4">
          <div className="flex min-w-0 items-baseline gap-3">
            <h1 className="truncate text-base font-bold text-slate-900">{test.title}</h1>
            <span className="hidden flex-shrink-0 text-sm text-slate-400 sm:block">
              Section {activeSection + 1} of {sections.length}
            </span>
          </div>
          <div className="flex flex-shrink-0 items-center gap-3">
            <div className="hidden w-40 lg:block">
              <ReadingProgress answered={answeredCount} total={flat.length} />
            </div>
            <ReadingTimer remaining={remaining} paused={paused} onPause={pause} onResume={resume} />
            <Button onClick={() => setConfirmOpen(true)}>
              <ListChecks className="h-4 w-4" /> Submit
            </Button>
          </div>
        </div>

        <ListeningAudioPlayer src={section.section.audio_url} sectionTitle={section.section.title} />

        <ListeningSectionNav
          sections={sections}
          active={activeSection}
          answers={answers}
          onSelect={selectSection}
        />
      </div>

      {/* Single-column questions for the active section */}
      <div className="mx-auto mt-3 max-w-3xl">
        <ListeningQuestions
          section={section}
          answers={answers}
          activeNumber={activeNumber}
          onAnswer={handleAnswer}
          onFocusQuestion={setActiveNumber}
        />
      </div>

      <SubmitConfirm
        open={confirmOpen}
        answered={answeredCount}
        total={flat.length}
        submitting={submitting}
        onConfirm={handleSubmit}
        onCancel={() => setConfirmOpen(false)}
      />
    </div>
  );
}
