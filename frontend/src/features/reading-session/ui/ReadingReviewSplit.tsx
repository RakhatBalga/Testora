"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import {
  CheckCircle2,
  XCircle,
  CircleDashed,
  MapPin,
  ChevronLeft,
  ChevronRight,
  ListFilter,
  RotateCcw,
} from "lucide-react";
import type { AttemptResult } from "@/shared/api";
import { Button } from "@/shared/ui";
import { EvidencePassage } from "./EvidencePassage";
import {
  evidenceLocation,
  rangeLabel,
  typeLabel,
  type NumberedQuestion,
  type ReadingGroup,
} from "../model/types";

type Props = {
  result: AttemptResult;
  groups: ReadingGroup[];
  onRetake: () => void;
};

function bandColor(band: number): string {
  if (band >= 7) return "text-green-600";
  if (band >= 5.5) return "text-amber-600";
  return "text-red-600";
}

export function ReadingReviewSplit({ result, groups, onRetake }: Props) {
  const byId = useMemo(
    () => new Map(result.answers.map((a) => [a.question_id, a])),
    [result.answers]
  );
  const flat = useMemo(() => groups.flatMap((g) => g.questions), [groups]);
  const [incorrectOnly, setIncorrectOnly] = useState(false);
  const visible = useMemo(
    () => incorrectOnly ? flat.filter((question) => !byId.get(question.id)?.is_correct) : flat,
    [byId, flat, incorrectOnly]
  );
  const [activeId, setActiveId] = useState<number | null>(flat[0]?.id ?? null);

  const active = useMemo(
    () => visible.find((q) => q.id === activeId) ?? visible[0],
    [visible, activeId]
  );
  const activeGroup = useMemo(
    () => groups.find((g) => g.questions.some((q) => q.id === active?.id)) ?? groups[0],
    [groups, active]
  );
  const activeSpans = active?.evidence ?? [];

  const leftRef = useRef<HTMLDivElement>(null);
  const activeIndex = visible.findIndex((question) => question.id === active?.id);

  // Auto-scroll the passage to the active question's evidence (or top).
  useEffect(() => {
    const first = activeSpans[0]?.paragraph;
    const id = requestAnimationFrame(() => {
      const container = leftRef.current;
      if (!container) return;
      if (first == null) {
        container.scrollTop = 0;
        return;
      }
      // Manual offset math (not scrollIntoView): centres the evidence paragraph
      // instantly, ignoring any CSS `scroll-behavior: smooth` that would
      // otherwise no-op under reduced-motion. Reads as "here it is".
      const target = container.querySelector<HTMLElement>(`#ev-para-${first}`);
      if (!target) return;
      const delta =
        target.getBoundingClientRect().top - container.getBoundingClientRect().top;
      container.scrollTop +=
        delta - (container.clientHeight - target.clientHeight) / 2;
    });
    return () => cancelAnimationFrame(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeId]);

  if (!active || !activeGroup) return null;

  return (
    <div className="relative left-1/2 flex h-[calc(100vh-8rem)] min-h-[480px] w-[95vw] max-w-[1600px] -translate-x-1/2 flex-col overflow-hidden">
      {/* Compact result header */}
      <div className="flex flex-shrink-0 items-center justify-between gap-4 pb-3">
        <div className="flex items-center gap-5">
          <h1 className="text-base font-bold text-slate-900">Review · {result.test_title}</h1>
          <div className="hidden items-center gap-4 text-sm sm:flex">
            <span className="text-slate-500">
              Score <strong className="text-slate-900">{result.correct}/{result.total}</strong>
            </span>
            <span className="text-slate-500">
              Band{" "}
              <strong className={bandColor(result.band ?? 0)}>
                {result.band !== null ? result.band.toFixed(1) : "—"}
              </strong>
            </span>
            <span className="text-slate-500">
              Accuracy <strong className="text-slate-900">{result.accuracy}%</strong>
            </span>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button variant={incorrectOnly ? "primary" : "secondary"} size="sm" disabled={result.incorrect === 0} onClick={() => setIncorrectOnly((value) => !value)}>
            <ListFilter className="h-4 w-4" /> Incorrect only
          </Button>
          {incorrectOnly && <><Button aria-label="Previous mistake" variant="secondary" size="sm" disabled={activeIndex <= 0} onClick={() => setActiveId(visible[activeIndex - 1]?.id ?? active.id)}><ChevronLeft className="h-4 w-4" /></Button><Button aria-label="Next mistake" variant="secondary" size="sm" disabled={activeIndex >= visible.length - 1} onClick={() => setActiveId(visible[activeIndex + 1]?.id ?? active.id)}><ChevronRight className="h-4 w-4" /></Button></>}
          <Button variant="secondary" size="sm" onClick={onRetake}>
            <RotateCcw className="h-4 w-4" /> Retake
          </Button>
        </div>
      </div>

      {result.breakdown.length > 0 && (
        <div className="mb-3 flex flex-shrink-0 flex-wrap items-center gap-2 text-xs">
          <span className="font-semibold text-slate-500">By question type</span>
          {result.breakdown.slice(0, 4).map((item) => (
            <span key={item.question_type} className="rounded-md bg-slate-100 px-2 py-1 text-slate-600">
              {item.label}: <strong>{item.accuracy}%</strong>
            </span>
          ))}
          <Link href={`/reading/${result.test_id}`} className="ml-auto font-semibold text-[var(--brand)] hover:underline">
            Practice {result.breakdown[0].label}
          </Link>
        </div>
      )}

      {/* Split: passage (with highlight) + review cards */}
      <div className="grid min-h-0 flex-1 grid-cols-1 grid-rows-[minmax(0,1fr)] gap-4 lg:grid-cols-[60fr_40fr] lg:gap-5 2xl:grid-cols-[65fr_35fr]">
        <div
          ref={leftRef}
          className="hidden min-h-0 overflow-y-auto rounded-2xl border border-[var(--border)] bg-white px-6 py-6 sm:px-8 lg:block"
        >
          <EvidencePassage section={activeGroup.section} activeSpans={activeSpans} />
        </div>

        <div className="min-h-0 overflow-y-auto rounded-2xl border border-[var(--border)] bg-white p-3.5 sm:p-4">
          {groups.map((g) => (
            <div key={g.section.id} className="mb-4 last:mb-0">
              <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-400">
                {rangeLabel(g.start, g.end)}
              </p>
              <div className="space-y-2.5">
                {g.questions.filter((q) => !incorrectOnly || !byId.get(q.id)?.is_correct).map((q) => (
                  <ReviewCard
                    key={q.id}
                    question={q}
                    answer={byId.get(q.id)}
                    active={q.id === active.id}
                    onSelect={() => setActiveId(q.id)}
                  />
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function ReviewCard({
  question,
  answer,
  active,
  onSelect,
}: {
  question: NumberedQuestion;
  answer: AttemptResult["answers"][number] | undefined;
  active: boolean;
  onSelect: () => void;
}) {
  const userAnswer = answer?.user_answer?.trim() ?? "";
  const answered = userAnswer !== "";
  const correct = !!answer?.is_correct;
  const location = evidenceLocation(question.evidence);

  const StatusIcon = !answered ? CircleDashed : correct ? CheckCircle2 : XCircle;
  const statusColor = !answered
    ? "text-slate-400"
    : correct
      ? "text-green-600"
      : "text-red-600";

  return (
    <button
      type="button"
      onClick={onSelect}
      className={`w-full rounded-xl border p-3 text-left transition ${
        active
          ? "border-[var(--brand)] ring-1 ring-[var(--brand)]/20"
          : "border-[var(--border)] hover:border-slate-300 hover:bg-slate-50"
      }`}
    >
      <div className="flex items-start gap-2.5">
        <span className="flex h-6 w-6 flex-shrink-0 items-center justify-center rounded-md bg-slate-100 text-xs font-bold text-slate-600">
          {question.number}
        </span>
        <div className="min-w-0 flex-1">
          <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-400">
            {typeLabel(question.question_type)}
          </p>
          <p className="mt-0.5 text-sm font-medium leading-snug text-slate-900">
            {answer?.text ?? question.text}
          </p>

          <div className="mt-2 space-y-1 text-sm">
            <span className={`flex items-center gap-1.5 ${statusColor}`}>
              <StatusIcon className="h-4 w-4 flex-shrink-0" />
              {answered ? (
                <span>
                  Your answer: <strong>{userAnswer}</strong>
                </span>
              ) : (
                <span>Not answered</span>
              )}
            </span>
            {!correct && answer && (
              <p className="pl-[22px] text-slate-600">
                Correct: <strong className="text-slate-900">{answer.correct_answer}</strong>
              </p>
            )}
          </div>

          {location ? (
            <span
              className={`mt-2 inline-flex items-center gap-1.5 rounded-md px-2 py-1 text-xs font-medium ${
                active ? "bg-yellow-100 text-yellow-800" : "bg-slate-50 text-slate-500"
              }`}
            >
              <MapPin className="h-3.5 w-3.5" />
              Evidence: {location}
            </span>
          ) : (
            <span className="mt-2 inline-block text-xs italic text-slate-400">
              Not stated in the passage
            </span>
          )}

          {answer?.explanation && active && (
            <p className="mt-2 rounded-lg bg-slate-50 px-2.5 py-1.5 text-xs leading-relaxed text-slate-600">
              {answer.explanation}
            </p>
          )}
        </div>
      </div>
    </button>
  );
}
