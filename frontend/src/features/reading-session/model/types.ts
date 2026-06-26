import type { EvidenceSpan, Question, Section, TestDetail, AnswerValue } from "@/shared/api";

/** A question with its global 1-based number across the whole test. */
export type NumberedQuestion = Question & { number: number };

/** A passage section plus its question range, e.g. "Questions 1–13". */
export type ReadingGroup = {
  section: Section;
  questions: NumberedQuestion[];
  start: number;
  end: number;
};

export type AnswerMap = Record<number, AnswerValue>;

/**
 * Flatten a test into passage groups, assigning each question a continuous
 * global number. Sections/questions are already ordered by the backend.
 */
export function buildGroups(test: TestDetail): ReadingGroup[] {
  const groups: ReadingGroup[] = [];
  let n = 0;
  for (const section of test.sections) {
    const questions: NumberedQuestion[] = section.questions.map((q) => {
      n += 1;
      return { ...q, number: n };
    });
    if (questions.length === 0) continue;
    groups.push({
      section,
      questions,
      start: questions[0].number,
      end: questions[questions.length - 1].number,
    });
  }
  return groups;
}

export function flattenQuestions(groups: ReadingGroup[]): NumberedQuestion[] {
  return groups.flatMap((g) => g.questions);
}

export function isAnswered(v: AnswerValue | undefined): boolean {
  if (Array.isArray(v)) return v.length > 0;
  return typeof v === "string" && v.trim() !== "";
}

export function rangeLabel(start: number, end: number): string {
  return start === end ? `Question ${start}` : `Questions ${start}–${end}`;
}

/** Short label for a question type, used as a group hint. */
export function typeLabel(type: Question["question_type"]): string {
  switch (type) {
    case "single_choice":
      return "Multiple choice";
    case "multiple_choice":
      return "Choose TWO";
    case "true_false_notgiven":
      return "True / False / Not Given";
    case "matching":
      return "Matching";
    case "fill_blank":
      return "Completion";
    case "short_answer":
      return "Short answer";
    default:
      return "";
  }
}

/** Human label for where evidence lives, e.g. "Paragraph 2" or "Paragraphs 4–5". */
export function evidenceLocation(spans: EvidenceSpan[] | null | undefined): string | null {
  if (!spans || spans.length === 0) return null;
  const paras = [...new Set(spans.map((s) => s.paragraph))].sort((a, b) => a - b);
  if (paras.length === 1) return `Paragraph ${paras[0]}`;
  const contiguous = paras.every((p, i) => i === 0 || p === paras[i - 1] + 1);
  if (contiguous) return `Paragraphs ${paras[0]}–${paras[paras.length - 1]}`;
  return `Paragraphs ${paras.join(", ")}`;
}

export function formatClock(totalSeconds: number): string {
  const safe = Math.max(0, totalSeconds);
  const m = Math.floor(safe / 60).toString().padStart(2, "0");
  const s = (safe % 60).toString().padStart(2, "0");
  return `${m}:${s}`;
}
