"use client";

import { Fragment, useEffect, useMemo, useState } from "react";
import { Sparkles, Wand2 } from "lucide-react";

/**
 * Premium "Your Response vs Better Version" comparison.
 *
 * There is no AI budget (AI_PROVIDER=mock), so the improved essay is produced by
 * a deterministic enhancement engine — the same philosophy as the mock grader.
 * Every edit it makes is recorded with its type + reason, so the diff highlights,
 * tooltips and stats bar all reflect *genuine* transformations rather than random
 * decoration. Swapping in a real model later = feed `improvedParagraphs` from the
 * backend instead of `improveParagraph`; the UI is untouched.
 */

type Criterion = "vocabulary" | "grammar" | "coherence" | "task";

type Segment =
  | { t: "same"; text: string }
  | { t: "added"; text: string; reason: string; criterion: Criterion }
  | { t: "replaced"; from: string; text: string; reason: string; criterion: Criterion }
  | { t: "removed"; text: string; reason: string; criterion: Criterion };

type Rule = {
  re: RegExp;
  kind: "replaced" | "removed";
  to?: string;
  reason: string;
  criterion: Criterion;
};

// Conservative, high-confidence ESL improvements. Order matters only for ties;
// overlaps are resolved by "earliest, then longest" below so phrase rules win
// over single-word rules (e.g. "very important" → "crucial" beats removing "very").
const RULES: Rule[] = [
  // Collocations & vocabulary (replaced → blue)
  { re: /\bvery important\b/gi, to: "crucial", kind: "replaced", reason: "More natural collocation", criterion: "vocabulary" },
  { re: /\bvery big\b/gi, to: "substantial", kind: "replaced", reason: "More natural collocation", criterion: "vocabulary" },
  { re: /\bvery good\b/gi, to: "excellent", kind: "replaced", reason: "More natural collocation", criterion: "vocabulary" },
  { re: /\bvery bad\b/gi, to: "detrimental", kind: "replaced", reason: "More natural collocation", criterion: "vocabulary" },
  { re: /\bbig problem\b/gi, to: "significant problem", kind: "replaced", reason: "More natural collocation", criterion: "vocabulary" },
  { re: /\ba lot of\b/gi, to: "a great deal of", kind: "replaced", reason: "More natural collocation", criterion: "vocabulary" },
  { re: /\blots of\b/gi, to: "numerous", kind: "replaced", reason: "Improved vocabulary", criterion: "vocabulary" },
  { re: /\bnowadays\b/gi, to: "in recent years", kind: "replaced", reason: "Improved vocabulary", criterion: "vocabulary" },
  { re: /\bkids\b/gi, to: "children", kind: "replaced", reason: "Improved vocabulary", criterion: "vocabulary" },
  { re: /\bgood example\b/gi, to: "compelling example", kind: "replaced", reason: "More specific example", criterion: "task" },
  { re: /\bfor example\b/gi, to: "for instance", kind: "replaced", reason: "More specific example", criterion: "task" },
  { re: /\bI think\b/gi, to: "I would argue", kind: "replaced", reason: "Stronger stance", criterion: "task" },

  // Grammar & register (replaced → green via criterion mapping)
  { re: /\bdon't\b/gi, to: "do not", kind: "replaced", reason: "Better grammar", criterion: "grammar" },
  { re: /\bdoesn't\b/gi, to: "does not", kind: "replaced", reason: "Better grammar", criterion: "grammar" },
  { re: /\bcan't\b/gi, to: "cannot", kind: "replaced", reason: "Better grammar", criterion: "grammar" },
  { re: /\bwon't\b/gi, to: "will not", kind: "replaced", reason: "Better grammar", criterion: "grammar" },
  { re: /\bit's\b/gi, to: "it is", kind: "replaced", reason: "Better grammar", criterion: "grammar" },
  { re: /\bthey're\b/gi, to: "they are", kind: "replaced", reason: "Better grammar", criterion: "grammar" },

  // Coherence / linking (replaced → blue)
  { re: /\bAlso,?\s/g, to: "Moreover, ", kind: "replaced", reason: "Improved coherence", criterion: "coherence" },
  { re: /\bAnd so\b/gi, to: "Consequently", kind: "replaced", reason: "Improved coherence", criterion: "coherence" },

  // Filler removal (removed → red strike-through)
  { re: /\breally\s/gi, kind: "removed", reason: "Tighter, more concise", criterion: "coherence" },
  { re: /\bbasically\s/gi, kind: "removed", reason: "Tighter, more concise", criterion: "coherence" },
  { re: /\bactually\s/gi, kind: "removed", reason: "Tighter, more concise", criterion: "coherence" },
];

type Match = { start: number; end: number; seg: Exclude<Segment, { t: "same" }> };

function improveParagraph(paragraph: string, index: number): Segment[] {
  const matches: Match[] = [];

  for (const rule of RULES) {
    const flags = rule.re.flags.includes("g") ? rule.re.flags : rule.re.flags + "g";
    const re = new RegExp(rule.re.source, flags);
    let m: RegExpExecArray | null;
    while ((m = re.exec(paragraph)) !== null) {
      const full = m[0];
      if (rule.kind === "removed") {
        matches.push({
          start: m.index,
          end: m.index + full.length,
          seg: { t: "removed", text: full, reason: rule.reason, criterion: rule.criterion },
        });
      } else {
        const preserveCase = full[0] === full[0].toUpperCase() && rule.to;
        const to = preserveCase ? rule.to!.charAt(0).toUpperCase() + rule.to!.slice(1) : rule.to!;
        matches.push({
          start: m.index,
          end: m.index + full.length,
          seg: { t: "replaced", from: full, text: to, reason: rule.reason, criterion: rule.criterion },
        });
      }
      if (m.index === re.lastIndex) re.lastIndex++;
    }
  }

  // Resolve overlaps: earliest start wins; on tie the longer match wins.
  matches.sort((a, b) => a.start - b.start || b.end - b.start - (a.end - a.start));
  const chosen: Match[] = [];
  let cursor = 0;
  for (const mt of matches) {
    if (mt.start >= cursor) {
      chosen.push(mt);
      cursor = mt.end;
    }
  }

  const segs: Segment[] = [];
  let i = 0;
  for (const mt of chosen) {
    if (mt.start > i) segs.push({ t: "same", text: paragraph.slice(i, mt.start) });
    segs.push(mt.seg);
    i = mt.end;
  }
  if (i < paragraph.length) segs.push({ t: "same", text: paragraph.slice(i) });

  // Coherence: open body paragraphs (after the first) with a linking adverbial
  // when they don't already start with one — a clear, common IELTS upgrade.
  if (index >= 1) {
    const opener = (segs[0]?.t === "same" ? segs[0].text : "").trimStart();
    const alreadyLinked = /^(however|moreover|furthermore|in addition|consequently|nevertheless|firstly|secondly|finally|in conclusion|to conclude)/i.test(opener);
    if (opener && !alreadyLinked) {
      const connector = index === 1 ? "Furthermore, " : "In addition, ";
      // lower-case the original first letter now that it follows a connector
      if (segs[0]?.t === "same") {
        segs[0] = { t: "same", text: segs[0].text.replace(/^(\s*)([A-Z])/, (_, sp, c) => sp + c.toLowerCase()) };
      }
      segs.unshift({ t: "added", text: connector, reason: "Improved coherence", criterion: "coherence" });
    }
  }

  return segs;
}

function cleanText(segs: Segment[]): string {
  return segs
    .map((s) => {
      if (s.t === "removed") return "";
      if (s.t === "same" || s.t === "added") return s.text;
      return s.text; // replaced → the improved wording
    })
    .join("");
}

const CRITERIA: { key: Criterion; label: string; noun: string }[] = [
  { key: "vocabulary", label: "Vocabulary", noun: "stronger collocations" },
  { key: "grammar", label: "Grammar", noun: "grammar fixes" },
  { key: "coherence", label: "Coherence", noun: "clearer transitions" },
  { key: "task", label: "Task Response", noun: "sharper points" },
];

type Props = {
  prompt: string;
  response: string;
};

export function EssayComparison({ prompt, response }: Props) {
  const [clean, setClean] = useState(false);
  const [glow, setGlow] = useState(true);

  // Glow only once on first paint, then settle.
  useEffect(() => {
    const id = window.setTimeout(() => setGlow(false), 900);
    return () => window.clearTimeout(id);
  }, []);

  const { originalParas, improvedParas, counts, total } = useMemo(() => {
    const original = response.split(/\n+/).map((p) => p.trim()).filter(Boolean);
    const improved = original.map((p, i) => improveParagraph(p, i));
    const counts: Record<Criterion, number> = { vocabulary: 0, grammar: 0, coherence: 0, task: 0 };
    let total = 0;
    for (const segs of improved) {
      for (const s of segs) {
        if (s.t !== "same") {
          counts[s.criterion] += 1;
          total += 1;
        }
      }
    }
    return { originalParas: original, improvedParas: improved, counts, total };
  }, [response]);

  const rows = Math.max(originalParas.length, improvedParas.length);

  const segClass = (t: Exclude<Segment["t"], "same">) =>
    t === "added" ? "diff-add" : t === "replaced" ? "diff-rep" : "diff-del";

  let markIndex = 0;
  const renderImproved = (segs: Segment[]) => {
    if (clean) return <>{cleanText(segs)}</>;
    return (
      <>
        {segs.map((s, i) => {
          if (s.t === "same") return <Fragment key={i}>{s.text}</Fragment>;
          const delay = Math.min(markIndex * 45, 520);
          markIndex += 1;
          return (
            <span
              key={i}
              className={`diff-mark ${segClass(s.t)} ${glow ? "diff-glow" : ""}`}
              style={glow ? { animationDelay: `${delay}ms` } : undefined}
            >
              {s.text}
              <span className="diff-tip">{s.reason}</span>
            </span>
          );
        })}
      </>
    );
  };

  return (
    <section className="space-y-5">
      {/* Prompt — full width */}
      <div className="rounded-[20px] border border-[var(--border)] bg-white p-6 shadow-sm shadow-slate-200/50 sm:p-7">
        <h2 className="mb-3 text-xs font-semibold uppercase tracking-[0.14em] text-slate-400">
          Prompt
        </h2>
        <p className="whitespace-pre-line text-[15px] leading-[1.8] text-slate-700">
          {prompt}
        </p>
      </div>

      {/* Sticky toggle */}
      <div className="sticky top-[64px] z-30 -mx-1 px-1">
        <div className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-[var(--border)] bg-white/85 px-3 py-2.5 shadow-sm shadow-slate-200/50 backdrop-blur">
          <div className="flex items-center gap-2 pl-1 text-sm font-semibold text-slate-700">
            <Wand2 className="h-4 w-4 text-[var(--brand)]" />
            Compare your essay
          </div>
          <div className="inline-flex rounded-xl bg-slate-100 p-1 text-sm font-medium">
            <button
              type="button"
              onClick={() => setClean(false)}
              aria-pressed={!clean}
              className={`rounded-lg px-3 py-1.5 transition-all duration-200 ${
                !clean ? "bg-white text-slate-900 shadow-sm" : "text-slate-500 hover:text-slate-700"
              }`}
            >
              Highlight changes
            </button>
            <button
              type="button"
              onClick={() => setClean(true)}
              aria-pressed={clean}
              className={`rounded-lg px-3 py-1.5 transition-all duration-200 ${
                clean ? "bg-white text-slate-900 shadow-sm" : "text-slate-500 hover:text-slate-700"
              }`}
            >
              Show clean version
            </button>
          </div>
        </div>
      </div>

      {/* Comparison panel */}
      <div className="overflow-hidden rounded-[20px] border border-[var(--border)] bg-white shadow-sm shadow-slate-200/50">
        {/* ---- Desktop: aligned two-column grid ---- */}
        <div className="hidden lg:grid lg:grid-cols-2">
          {/* Column headers */}
          <div className="border-b border-r border-[var(--border)] px-7 pt-6 pb-4">
            <h3 className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-400">
              Your Response
            </h3>
          </div>
          <div className="border-b border-[var(--border)] bg-gradient-to-b from-emerald-50/40 to-transparent px-7 pt-6 pb-4">
            <div className="flex items-center gap-2">
              <h3 className="text-xs font-semibold uppercase tracking-[0.14em] text-emerald-700">
                Better Version
              </h3>
              <Sparkles className="h-3.5 w-3.5 text-emerald-500" />
            </div>
            <StatsBar counts={counts} />
          </div>

          {/* Paragraph rows */}
          {Array.from({ length: rows }).map((_, i) => (
            <Fragment key={i}>
              <p className="border-r border-[var(--border)] px-7 py-4 text-[15px] leading-[1.8] text-slate-600">
                {originalParas[i] ?? ""}
              </p>
              <p className="bg-emerald-50/20 px-7 py-4 text-[15px] leading-[1.8] text-slate-800">
                {improvedParas[i] ? renderImproved(improvedParas[i]) : ""}
              </p>
            </Fragment>
          ))}
        </div>

        {/* ---- Mobile: stacked ---- */}
        <div className="lg:hidden">
          <div className="border-b border-[var(--border)] px-6 py-5">
            <h3 className="mb-3 text-xs font-semibold uppercase tracking-[0.14em] text-slate-400">
              Your Response
            </h3>
            <div className="space-y-3">
              {originalParas.map((p, i) => (
                <p key={i} className="text-[15px] leading-[1.8] text-slate-600">
                  {p}
                </p>
              ))}
            </div>
          </div>
          <div className="bg-emerald-50/20 px-6 py-5">
            <div className="mb-1 flex items-center gap-2">
              <h3 className="text-xs font-semibold uppercase tracking-[0.14em] text-emerald-700">
                Better Version
              </h3>
              <Sparkles className="h-3.5 w-3.5 text-emerald-500" />
            </div>
            <StatsBar counts={counts} />
            <div className="mt-4 space-y-3">
              {improvedParas.map((segs, i) => (
                <p key={i} className="text-[15px] leading-[1.8] text-slate-800">
                  {renderImproved(segs)}
                </p>
              ))}
            </div>
          </div>
        </div>
      </div>

      {total === 0 && (
        <p className="px-1 text-sm text-slate-500">
          No high-confidence edits found — this response already reads cleanly.
        </p>
      )}
    </section>
  );
}

function StatsBar({ counts }: { counts: Record<Criterion, number> }) {
  return (
    <div className="mt-3 flex flex-wrap gap-2">
      {CRITERIA.map(({ key, label, noun }) => {
        const n = counts[key];
        const active = n > 0;
        return (
          <span
            key={key}
            className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-medium transition-colors ${
              active
                ? "border-emerald-200 bg-emerald-50 text-emerald-700"
                : "border-slate-200 bg-slate-50 text-slate-400"
            }`}
            title={active ? `+${n} ${noun}` : "No changes"}
          >
            {label}
            <span aria-hidden className={active ? "text-emerald-500" : "text-slate-300"}>
              ↑
            </span>
            {active && (
              <span className="rounded-full bg-emerald-500/10 px-1.5 py-0.5 text-[10px] font-semibold text-emerald-700">
                +{n} {noun}
              </span>
            )}
          </span>
        );
      })}
    </div>
  );
}
