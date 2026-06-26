import type { AnswerValue } from "@/shared/api";
import { ListeningQuestionCard } from "./ListeningQuestionCard";
import { rangeLabel, type AnswerMap, type ReadingGroup } from "@/features/reading-session";

type Props = {
  section: ReadingGroup;
  answers: AnswerMap;
  activeNumber: number | null;
  onAnswer: (questionId: number, value: AnswerValue) => void;
  onFocusQuestion: (number: number) => void;
};

export function ListeningQuestions({
  section,
  answers,
  activeNumber,
  onAnswer,
  onFocusQuestion,
}: Props) {
  return (
    <div>
      <div className="mb-2.5">
        <div className="flex items-baseline gap-2">
          <h2 className="text-sm font-bold text-slate-900">{section.section.title}</h2>
          <span className="text-xs font-semibold text-[var(--brand)]">
            {rangeLabel(section.start, section.end)}
          </span>
        </div>
        {section.section.instructions && (
          <p className="mt-0.5 text-xs leading-snug text-slate-500">
            {section.section.instructions}
          </p>
        )}
      </div>
      <div className="space-y-2">
        {section.questions.map((q) => (
          <ListeningQuestionCard
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
