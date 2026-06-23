"use client";

import { Flag } from "lucide-react";

export type PaletteItem = {
  id: number;
  number: number;
  sectionTitle: string;
  answered: boolean;
  marked: boolean;
};

/**
 * IELTS-style question palette: every question number, grouped by section,
 * coloured by state (current / answered / marked / unanswered). Click to jump.
 */
export function QuestionPalette({
  items,
  currentId,
  onJump,
}: {
  items: PaletteItem[];
  currentId: number | null;
  onJump: (id: number) => void;
}) {
  // Preserve section order as it appears in `items`.
  const sections: { title: string; items: PaletteItem[] }[] = [];
  for (const it of items) {
    let group = sections.find((s) => s.title === it.sectionTitle);
    if (!group) {
      group = { title: it.sectionTitle, items: [] };
      sections.push(group);
    }
    group.items.push(it);
  }

  return (
    <div className="space-y-3">
      {sections.map((section) => (
        <div key={section.title}>
          <p className="mb-1.5 text-[0.7rem] font-semibold uppercase tracking-wide text-[var(--text-secondary)]">
            {section.title}
          </p>
          <div className="flex flex-wrap gap-1.5">
            {section.items.map((it) => {
              const isCurrent = it.id === currentId;
              const base =
                "relative flex h-8 w-8 items-center justify-center rounded-lg text-xs font-semibold transition";
              const state = isCurrent
                ? "bg-[var(--brand)] text-white ring-2 ring-[var(--brand)] ring-offset-1"
                : it.answered
                  ? "bg-[var(--brand)]/[0.12] text-[var(--brand)] hover:bg-[var(--brand)]/20"
                  : "bg-slate-100 text-slate-500 hover:bg-slate-200";
              return (
                <button
                  key={it.id}
                  type="button"
                  onClick={() => onJump(it.id)}
                  className={`${base} ${state}`}
                  aria-label={`Question ${it.number}${it.marked ? " (marked for review)" : ""}`}
                >
                  {it.number}
                  {it.marked && (
                    <Flag className="absolute -right-1 -top-1 h-3 w-3 rounded-full bg-white p-[1px] text-amber-500" />
                  )}
                </button>
              );
            })}
          </div>
        </div>
      ))}

      <div className="flex flex-wrap gap-3 pt-1 text-[0.7rem] text-[var(--text-secondary)]">
        <Legend className="bg-[var(--brand)]" label="Current" />
        <Legend className="bg-[var(--brand)]/[0.12]" label="Answered" />
        <Legend className="bg-slate-100" label="Unanswered" />
        <span className="inline-flex items-center gap-1.5">
          <Flag className="h-3 w-3 text-amber-500" />
          Marked
        </span>
      </div>
    </div>
  );
}

function Legend({ className, label }: { className: string; label: string }) {
  return (
    <span className="inline-flex items-center gap-1.5">
      <span className={`h-3 w-3 rounded ${className}`} />
      {label}
    </span>
  );
}
