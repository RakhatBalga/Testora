import type { AnswerValue } from "@/lib/api";
import { typeLabel, type NumberedQuestion } from "./types";

type Props = {
  question: NumberedQuestion;
  value: AnswerValue;
  active: boolean;
  onChange: (value: AnswerValue) => void;
  onFocus: () => void;
};

/** Radio list for single-answer choice types (MCQ, TFNG, Yes/No/NG). */
function RadioGroup({
  question,
  value,
  onChange,
}: {
  question: NumberedQuestion;
  value: AnswerValue;
  onChange: (v: AnswerValue) => void;
}) {
  return (
    <div className="space-y-1.5">
      {question.options!.map((option, i) => {
        const selected = value === option;
        const letter = String.fromCharCode(65 + i);
        return (
          <label
            key={option}
            className={`flex cursor-pointer items-center gap-3 rounded-lg border px-3 py-2 text-sm transition ${
              selected
                ? "border-[var(--brand)] bg-[var(--brand)]/[0.06] ring-1 ring-[var(--brand)]/20"
                : "border-slate-200 hover:border-slate-300 hover:bg-slate-50"
            }`}
          >
            <span
              className={`flex h-5 w-5 flex-shrink-0 items-center justify-center rounded-full border text-[10px] font-bold ${
                selected
                  ? "border-[var(--brand)] bg-[var(--brand)] text-white"
                  : "border-slate-300 text-slate-400"
              }`}
            >
              {letter}
            </span>
            <input
              type="radio"
              name={`q-${question.id}`}
              checked={selected}
              onChange={() => onChange(option)}
              className="sr-only"
            />
            <span className="text-slate-700">{option}</span>
          </label>
        );
      })}
    </div>
  );
}

/** Checkbox list for "choose TWO" multiple-answer questions. */
function CheckboxGroup({
  question,
  value,
  onChange,
}: {
  question: NumberedQuestion;
  value: AnswerValue;
  onChange: (v: AnswerValue) => void;
}) {
  const selected = Array.isArray(value) ? value : [];
  const toggle = (option: string) =>
    onChange(
      selected.includes(option)
        ? selected.filter((o) => o !== option)
        : [...selected, option]
    );
  return (
    <div className="space-y-2">
      {question.options!.map((option) => {
        const checked = selected.includes(option);
        return (
          <label
            key={option}
            className={`flex cursor-pointer items-center gap-3 rounded-xl border px-3.5 py-2.5 text-sm transition ${
              checked
                ? "border-[var(--brand)] bg-[var(--brand)]/[0.06] ring-1 ring-[var(--brand)]/20"
                : "border-slate-200 hover:border-slate-300 hover:bg-slate-50"
            }`}
          >
            <span
              className={`flex h-5 w-5 flex-shrink-0 items-center justify-center rounded-md border-2 ${
                checked ? "border-[var(--brand)] bg-[var(--brand)]" : "border-slate-300"
              }`}
            >
              {checked && (
                <svg className="h-3 w-3 text-white" viewBox="0 0 20 20" fill="currentColor">
                  <path
                    fillRule="evenodd"
                    d="M16.7 5.3a1 1 0 010 1.4l-8 8a1 1 0 01-1.4 0l-4-4a1 1 0 011.4-1.4L8 12.6l7.3-7.3a1 1 0 011.4 0z"
                    clipRule="evenodd"
                  />
                </svg>
              )}
            </span>
            <input
              type="checkbox"
              checked={checked}
              onChange={() => toggle(option)}
              className="sr-only"
            />
            <span className="text-slate-700">{option}</span>
          </label>
        );
      })}
    </div>
  );
}

/** Dropdown selector for matching (headings / information / features). */
function MatchSelect({
  question,
  value,
  onChange,
}: {
  question: NumberedQuestion;
  value: AnswerValue;
  onChange: (v: AnswerValue) => void;
}) {
  return (
    <select
      value={typeof value === "string" ? value : ""}
      onChange={(e) => onChange(e.target.value)}
      className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-700 outline-none transition focus:border-[var(--brand)] focus:ring-2 focus:ring-[var(--brand)]/20"
    >
      <option value="">Select an answer…</option>
      {question.options!.map((option) => (
        <option key={option} value={option}>
          {option}
        </option>
      ))}
    </select>
  );
}

/** Free-text input for sentence/summary completion and short answers. */
function TextEntry({
  value,
  onChange,
}: {
  value: AnswerValue;
  onChange: (v: AnswerValue) => void;
}) {
  return (
    <input
      type="text"
      value={typeof value === "string" ? value : ""}
      onChange={(e) => onChange(e.target.value)}
      placeholder="Type your answer"
      className="w-full max-w-sm rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm outline-none transition focus:border-[var(--brand)] focus:ring-2 focus:ring-[var(--brand)]/20"
    />
  );
}

function Input({ question, value, onChange }: Omit<Props, "active" | "onFocus">) {
  switch (question.question_type) {
    case "multiple_choice":
      return <CheckboxGroup question={question} value={value} onChange={onChange} />;
    case "matching":
      return <MatchSelect question={question} value={value} onChange={onChange} />;
    case "fill_blank":
    case "short_answer":
      return <TextEntry value={value} onChange={onChange} />;
    case "single_choice":
    case "true_false_notgiven":
    default:
      return question.options ? (
        <RadioGroup question={question} value={value} onChange={onChange} />
      ) : (
        <TextEntry value={value} onChange={onChange} />
      );
  }
}

export function ReadingQuestionCard({ question, value, active, onChange, onFocus }: Props) {
  return (
    <div
      id={`q-${question.number}`}
      onFocusCapture={onFocus}
      onClick={onFocus}
      className={`scroll-mt-28 rounded-xl border bg-white p-3.5 transition ${
        active ? "border-[var(--brand)]/40 shadow-sm" : "border-[var(--border)]"
      }`}
    >
      <div className="mb-2.5 flex items-start gap-2.5">
        <span className="flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-lg bg-[var(--brand)]/[0.1] text-sm font-bold text-[var(--brand)]">
          {question.number}
        </span>
        <div className="min-w-0">
          <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-400">
            {typeLabel(question.question_type)}
          </p>
          <p className="mt-0.5 font-medium leading-snug text-slate-900">{question.text}</p>
        </div>
      </div>
      <div className="pl-[38px]">
        <Input question={question} value={value} onChange={onChange} />
      </div>
    </div>
  );
}
