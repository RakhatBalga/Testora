import { Fragment, type ReactNode } from "react";
import type { EvidenceSpan, Section } from "@/shared/api";
import { parsePassage } from "./ReadingPassage";

/** Build a whitespace-tolerant, case-insensitive regex matching any span text. */
function buildRegex(texts: string[]): RegExp | null {
  if (texts.length === 0) return null;
  const escaped = texts
    .map((t) => t.trim())
    .filter(Boolean)
    .map((t) => t.replace(/[.*+?^${}()|[\]\\]/g, "\\$&").replace(/\s+/g, "\\s+"));
  if (escaped.length === 0) return null;
  return new RegExp(`(${escaped.join("|")})`, "gi");
}

/** Render paragraph text with evidence spans wrapped in a soft highlight. The
 *  raw passage uses **keyword** markers for the exam view; we strip them here so
 *  evidence is the only highlight in review. */
function renderParagraph(text: string, texts: string[]): ReactNode {
  const clean = text.replace(/\*\*/g, "");
  const re = buildRegex(texts);
  if (!re) return clean;
  const chunks = clean.split(re);
  return chunks.map((chunk, i) =>
    chunk && i % 2 === 1 ? (
      <mark
        key={i}
        className="rounded bg-yellow-200/70 px-0.5 text-slate-900 transition-colors"
      >
        {chunk}
      </mark>
    ) : (
      <Fragment key={i}>{chunk}</Fragment>
    )
  );
}

type Props = {
  section: Section;
  /** Evidence spans for the currently selected question (this section only). */
  activeSpans: EvidenceSpan[];
};

/**
 * Read-only passage for Reading Review. Identical typography to the exam
 * passage, but highlights the active question's evidence and exposes a stable
 * id per paragraph (`ev-para-N`) so the parent can auto-scroll to it.
 */
export function EvidencePassage({ section, activeSpans }: Props) {
  const { heading, paras } = parsePassage(section.passage ?? "");

  return (
    <article className="mx-auto max-w-[76ch]">
      <p className="text-xs font-semibold uppercase tracking-wide text-[var(--brand)]">
        {section.title}
      </p>
      {heading && (
        <h2 className="mt-1.5 text-[1.75rem] font-bold leading-tight tracking-tight text-slate-900">
          {heading}
        </h2>
      )}

      <div className="mt-5 space-y-5">
        {paras.map((p, i) => {
          const texts = p.label
            ? activeSpans.filter((s) => String(s.paragraph) === p.label).map((s) => s.text)
            : [];
          return (
            <div key={i} id={p.label ? `ev-para-${p.label}` : undefined} className="flex gap-3.5">
              {p.label && (
                <span className="mt-1 w-4 flex-shrink-0 select-none text-right text-sm font-semibold text-slate-300">
                  {p.label}
                </span>
              )}
              <p className="flex-1 text-[1.125rem] leading-[1.8] text-slate-700">
                {renderParagraph(p.text, texts)}
              </p>
            </div>
          );
        })}
      </div>
    </article>
  );
}
