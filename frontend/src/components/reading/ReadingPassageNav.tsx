import { isAnswered, type AnswerMap, type ReadingGroup } from "./types";

type Props = {
  groups: ReadingGroup[];
  active: number;
  answers: AnswerMap;
  onSelect: (index: number) => void;
};

/** Passage tabs — the single navigation method. Only one passage is active at
 *  a time; each tab shows its question range and answered count. */
export function ReadingPassageNav({ groups, active, answers, onSelect }: Props) {
  return (
    <div className="flex gap-1 rounded-lg border border-[var(--border)] bg-slate-50 p-0.5">
      {groups.map((g, i) => {
        const answered = g.questions.filter((q) => isAnswered(answers[q.id])).length;
        const done = answered === g.questions.length;
        const isActive = i === active;
        return (
          <button
            key={g.section.id}
            type="button"
            onClick={() => onSelect(i)}
            className={`flex flex-1 items-center justify-center gap-1.5 rounded-md px-2 py-1.5 text-center transition ${
              isActive ? "bg-white shadow-sm" : "hover:bg-white/60"
            }`}
          >
            <span
              className={`text-sm font-semibold ${isActive ? "text-[var(--brand)]" : "text-slate-600"}`}
            >
              Passage {i + 1}
            </span>
            <span
              className={`text-[11px] tabular-nums ${
                done ? "font-semibold text-emerald-600" : "text-slate-400"
              }`}
            >
              {g.start}–{g.end}
              {done ? " ✓" : ""}
            </span>
          </button>
        );
      })}
    </div>
  );
}
