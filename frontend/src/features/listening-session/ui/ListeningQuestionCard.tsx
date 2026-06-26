import type { AnswerValue } from "@/shared/api";
import type { NumberedQuestion } from "@/features/reading-session";

type Props = {
  question: NumberedQuestion;
  value: AnswerValue;
  active: boolean;
  onChange: (value: AnswerValue) => void;
  onFocus: () => void;
};

function RadioRow({ question, value, onChange }: Omit<Props, "active" | "onFocus">) {
  return (
    <div className="space-y-1.5">
      {question.options!.map((option, i) => {
        const selected = value === option;
        const letter = String.fromCharCode(65 + i);
        return (
          <label
            key={option}
            className={`flex cursor-pointer items-center gap-3 rounded-lg border px-3 py-1.5 text-sm transition ${
              selected
                ? "border-[var(--brand)] bg-[var(--brand)]/[0.06] ring-1 ring-[var(--brand)]/20"
                : "border-slate-200 hover:border-slate-300 hover:bg-slate-50"
            }`}
          >
            <span
              className={`flex h-5 w-5 flex-shrink-0 items-center justify-center rounded-full border text-[10px] font-bold ${
                selected ? "border-[var(--brand)] bg-[var(--brand)] text-white" : "border-slate-300 text-slate-400"
              }`}
            >
              {letter}
            </span>
            <input type="radio" name={`q-${question.id}`} checked={selected} onChange={() => onChange(option)} className="sr-only" />
            <span className="text-slate-700">{option}</span>
          </label>
        );
      })}
    </div>
  );
}

function CheckboxRow({ question, value, onChange }: Omit<Props, "active" | "onFocus">) {
  const selected = Array.isArray(value) ? value : [];
  const toggle = (o: string) =>
    onChange(selected.includes(o) ? selected.filter((x) => x !== o) : [...selected, o]);
  return (
    <div className="space-y-1.5">
      {question.options!.map((option) => {
        const checked = selected.includes(option);
        return (
          <label
            key={option}
            className={`flex cursor-pointer items-center gap-3 rounded-lg border px-3 py-1.5 text-sm transition ${
              checked ? "border-[var(--brand)] bg-[var(--brand)]/[0.06]" : "border-slate-200 hover:bg-slate-50"
            }`}
          >
            <span className={`flex h-5 w-5 items-center justify-center rounded-md border-2 ${checked ? "border-[var(--brand)] bg-[var(--brand)]" : "border-slate-300"}`}>
              {checked && (
                <svg className="h-3 w-3 text-white" viewBox="0 0 20 20" fill="currentColor">
                  <path fillRule="evenodd" d="M16.7 5.3a1 1 0 010 1.4l-8 8a1 1 0 01-1.4 0l-4-4a1 1 0 011.4-1.4L8 12.6l7.3-7.3a1 1 0 011.4 0z" clipRule="evenodd" />
                </svg>
              )}
            </span>
            <input type="checkbox" checked={checked} onChange={() => toggle(option)} className="sr-only" />
            <span className="text-slate-700">{option}</span>
          </label>
        );
      })}
    </div>
  );
}

function Field({ question, value, active, onChange, onFocus }: Props) {
  const type = question.question_type;

  if (
    type === "single_choice" ||
    type === "true_false_notgiven" ||
    type === "yes_no_not_given"
  ) {
    return question.options ? <RadioRow question={question} value={value} onChange={onChange} /> : null;
  }
  if (type === "multiple_choice") {
    return <CheckboxRow question={question} value={value} onChange={onChange} />;
  }
  if (
    type === "matching" ||
    type === "matching_headings" ||
    type === "matching_information"
  ) {
    return (
      <select
        value={typeof value === "string" ? value : ""}
        onChange={(e) => onChange(e.target.value)}
        onFocus={onFocus}
        className="w-44 rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-700 outline-none transition focus:border-[var(--brand)] focus:ring-2 focus:ring-[var(--brand)]/20"
      >
        <option value="">— select —</option>
        {question.options!.map((o) => (
          <option key={o} value={o}>{o}</option>
        ))}
      </select>
    );
  }
  // fill_blank / short_answer (form / note / table / sentence completion)
  return (
    <input
      type="text"
      value={typeof value === "string" ? value : ""}
      onChange={(e) => onChange(e.target.value)}
      onFocus={onFocus}
      placeholder="Type your answer"
      className={`w-64 rounded-lg border bg-white px-3 py-2 text-sm outline-none transition focus:border-[var(--brand)] focus:ring-2 focus:ring-[var(--brand)]/20 ${
        active ? "border-[var(--brand)]/40" : "border-slate-300"
      }`}
    />
  );
}

/**
 * One listening question in a single-column row: number + prompt on the left,
 * the input beside or beneath it. Completion types (form/note/table/sentence)
 * use a compact text field; choices use radios; matching/map use a dropdown.
 */
export function ListeningQuestionCard(props: Props) {
  const { question, active, onFocus } = props;
  const isChoice =
    question.question_type === "single_choice" ||
    question.question_type === "multiple_choice" ||
    question.question_type === "true_false_notgiven" ||
    question.question_type === "yes_no_not_given";

  return (
    <div
      id={`q-${question.number}`}
      onClick={onFocus}
      className={`scroll-mt-4 rounded-lg border bg-white px-3 py-2.5 transition ${
        active ? "border-[var(--brand)]/40 shadow-sm" : "border-[var(--border)]"
      }`}
    >
      <div className={isChoice ? "" : "flex flex-wrap items-center gap-x-3 gap-y-1.5"}>
        <p className="flex items-baseline gap-2 text-sm font-medium leading-snug text-slate-900">
          <span className="flex h-5 w-5 flex-shrink-0 items-center justify-center rounded-md bg-[var(--brand)]/[0.1] text-[11px] font-bold text-[var(--brand)]">
            {question.number}
          </span>
          <span>{question.text}</span>
        </p>
        <div className={isChoice ? "mt-2 pl-7" : ""}>
          <Field {...props} />
        </div>
      </div>
    </div>
  );
}
