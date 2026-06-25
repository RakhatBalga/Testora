import { Fragment, type ReactNode } from "react";
import type { Section } from "@/lib/api";

/** Split a paragraph on **keyword** markers and render the keywords highlighted. */
function renderInline(text: string): ReactNode[] {
  return text.split(/(\*\*[^*]+\*\*)/g).map((chunk, i) => {
    if (chunk.startsWith("**") && chunk.endsWith("**")) {
      return (
        <mark
          key={i}
          className="rounded bg-amber-100/70 px-0.5 font-medium text-slate-900"
        >
          {chunk.slice(2, -2)}
        </mark>
      );
    }
    return <Fragment key={i}>{chunk}</Fragment>;
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

export function ReadingPassage({ section }: { section: Section }) {
  const { heading, paras } = parsePassage(section.passage ?? "");

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
              {renderInline(p.text)}
            </p>
          </div>
        ))}
      </div>
    </article>
  );
}
