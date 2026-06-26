import type { AnswerValue } from "@/shared/api";
import { ReadingQuestionCard } from "./ReadingQuestionCard";
import { rangeLabel, type AnswerMap, type ReadingGroup } from "../model/types";

type Props = {
  group: ReadingGroup;
  answers: AnswerMap;
  activeNumber: number | null;
  onAnswer: (questionId: number, value: AnswerValue) => void;
  onFocusQuestion: (number: number) => void;
};

/** Questions for the single active passage. Header is a normal heading (not
 *  sticky) — the panel scrolls independently, so a sticky band felt broken. */
export function ReadingQuestions({
  group,
  answers,
  activeNumber,
  onAnswer,
  onFocusQuestion,
}: Props) {
  return (
    <div>
      <div className="mb-4 border-b border-[var(--border)] pb-3">
        <h3 className="text-sm font-bold text-slate-900">{rangeLabel(group.start, group.end)}</h3>
        {group.section.instructions && (
          <p className="mt-1 text-xs leading-relaxed text-slate-500">
            {group.section.instructions}
          </p>
        )}
      </div>
      <div className="space-y-2.5">
        {group.questions.map((q) => (
          <ReadingQuestionCard
            key={q.id}
            question={q}
            value={answers[q.id] ?? null}
            active={activeNumber === q.number}
            onChange={(v) => onAnswer(q.id, v)}
            onFocus={() => onFocusQuestion(q.number)}
          />
        ))}
      </div>
    </div>
  );
}
