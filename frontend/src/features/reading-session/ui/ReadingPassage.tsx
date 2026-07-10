import { Fragment, type ReactNode } from "react";
import type { Section } from "@/shared/api";

/** Whitespace-tolerant, case-insensitive, word-bounded regex for saved words. */
function buildHighlightRegex(words: string[]): RegExp | null {
  const escaped = words
    .map((w) => w.trim())
    .filter(Boolean)
    .map((w) => w.replace(/[.*+?^${}()|[\]\\]/g, "\\$&").replace(/\s+/g, "\\s+"));
  if (escaped.length === 0) return null;
  // Longest first so a saved phrase wins over its component words.
  escaped.sort((a, b) => b.length - a.length);
  return new RegExp(`\\b(${escaped.join("|")})\\b`, "gi");
}

/**
 * Render a paragraph. `**keyword**` markers become the passage's own amber
 * highlight; saved vocabulary words get a yellow highlighter marker (persistent,
 * Engnovate-style) so the reader can see everything they've collected.
 */
function renderInline(text: string, highlightRe: RegExp | null): ReactNode[] {
  return text.split(/(\*\*[^*]+\*\*)/g).flatMap((chunk, i) => {
    if (chunk.startsWith("**") && chunk.endsWith("**")) {
      return [
        <mark
          key={`k${i}`}
          className="rounded bg-amber-100/70 px-0.5 font-medium text-slate-900"
        >
          {chunk.slice(2, -2)}
        </mark>,
      ];
    }
    if (!highlightRe) return [<Fragment key={`t${i}`}>{chunk}</Fragment>];
    // split() with a capturing regex keeps the matches at odd indices.
    return chunk.split(highlightRe).map((part, j) =>
      j % 2 === 1 ? (
        <mark
          key={`s${i}-${j}`}
          className="rounded bg-yellow-200/70 px-0.5 text-slate-900 transition-colors"
        >
          {part}
        </mark>
      ) : (
        <Fragment key={`t${i}-${j}`}>{part}</Fragment>
      ),
    );
  });
}

export type Para = { label: string | null; text: string };

/**
 * Parse the stored passage. The first non-marked line is treated as the
 * heading. Lines beginning with "¶N " become numbered paragraphs; everything
 * else is a plain paragraph. This keeps the schema a single text field while
 * supporting headings, numbered paragraphs and highlighted keywords.
 */
export function parsePassage(raw: string): { heading: string | null; paras: Para[] } {
  const blocks = raw
    .split(/\n{2,}/)
    .map((b) => b.trim())
    .filter(Boolean);

  let heading: string | null = null;
  const paras: Para[] = [];

  for (const block of blocks) {
    const m = block.match(/^¶(\S+)\s+([\s\S]*)$/);
    if (m) {
      paras.push({ label: m[1], text: m[2] });
    } else if (heading === null && paras.length === 0) {
      heading = block;
    } else {
      paras.push({ label: null, text: block });
    }
  }
  return { heading, paras };
}

export function ReadingPassage({
  section,
  highlights,
}: {
  section: Section;
  /** Saved words to highlight in the passage (case-insensitive, whole-word). */
  highlights?: string[];
}) {
  const { heading, paras } = parsePassage(section.passage ?? "");
  const highlightRe =
    highlights && highlights.length ? buildHighlightRegex(highlights) : null;

  return (
    <article className="mx-auto max-w-[76ch]">
      {heading && (
        <h2 className="text-[1.75rem] font-bold leading-tight tracking-tight text-slate-900">
          {heading}
        </h2>
      )}

      <div className="mt-5 space-y-5">
        {paras.map((p, i) => (
          <div key={i} className="flex gap-3.5">
            {p.label && (
              <span className="mt-1 w-4 flex-shrink-0 select-none text-right text-sm font-semibold text-slate-300">
                {p.label}
              </span>
            )}
            <p className="flex-1 text-[1.125rem] leading-[1.8] text-slate-700">
              {renderInline(p.text, highlightRe)}
            </p>
          </div>
        ))}
      </div>
    </article>
  );
}
