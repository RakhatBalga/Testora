import { Question, AnswerValue } from "@/lib/api";

type Props = {
  question: Question;
  value: AnswerValue;
  onChange: (value: AnswerValue) => void;
};

export function QuestionInput({ question, value, onChange }: Props) {
  const isText =
    question.question_type === "fill_blank" ||
    question.question_type === "short_answer" ||
    !question.options;

  if (isText) {
    return (
      <input
        type="text"
        value={typeof value === "string" ? value : ""}
        onChange={(e) => onChange(e.target.value)}
        placeholder="Type your answer"
        className="w-full max-w-md rounded-xl border border-slate-300 bg-white px-3.5 py-2.5 outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20"
      />
    );
  }

  if (question.question_type === "multiple_choice") {
    const selected = Array.isArray(value) ? value : [];
    const toggle = (option: string) => {
      onChange(
        selected.includes(option)
          ? selected.filter((o) => o !== option)
          : [...selected, option]
      );
    };
    return (
      <div className="space-y-2">
        {question.options!.map((option) => {
          const checked = selected.includes(option);
          return (
            <label
              key={option}
              className={`flex cursor-pointer items-center gap-3 rounded-xl border px-4 py-3 transition ${
                checked
                  ? "border-blue-500 bg-blue-50 ring-1 ring-blue-500/20"
                  : "border-slate-200 hover:border-slate-300 hover:bg-slate-50"
              }`}
            >
              <span
                className={`flex h-4 w-4 items-center justify-center rounded border-2 ${
                  checked ? "border-blue-600 bg-blue-600" : "border-slate-300"
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

  // single_choice | true_false_notgiven | matching
  return (
    <div className="space-y-2">
      {question.options!.map((option) => {
        const selected = value === option;
        return (
          <label
            key={option}
            className={`flex cursor-pointer items-center gap-3 rounded-xl border px-4 py-3 transition ${
              selected
                ? "border-blue-500 bg-blue-50 ring-1 ring-blue-500/20"
                : "border-slate-200 hover:border-slate-300 hover:bg-slate-50"
            }`}
          >
            <span
              className={`flex h-4 w-4 items-center justify-center rounded-full border-2 ${
                selected ? "border-blue-600" : "border-slate-300"
              }`}
            >
              {selected && <span className="h-2 w-2 rounded-full bg-blue-600" />}
            </span>
            <input
              type="radio"
              name={`q-${question.id}`}
              value={option}
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
