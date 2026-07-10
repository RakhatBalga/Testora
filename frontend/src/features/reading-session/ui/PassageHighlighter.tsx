"use client";

import { useCallback, useEffect, useState } from "react";
import { Eraser, Highlighter, X } from "lucide-react";

export type HlColor = "yellow" | "green" | "pink" | "blue";
export type Brush = HlColor | "eraser" | null;

type Mark = { passage: number; para: number; start: number; end: number; color: HlColor };

const COLORS: { key: HlColor; label: string; swatch: string }[] = [
  { key: "yellow", label: "Yellow", swatch: "bg-yellow-300" },
  { key: "green", label: "Green", swatch: "bg-green-300" },
  { key: "pink", label: "Pink", swatch: "bg-pink-300" },
  { key: "blue", label: "Blue", swatch: "bg-blue-300" },
];
const ALL_COLORS: HlColor[] = ["yellow", "green", "pink", "blue"];

// --- CSS Custom Highlight API access (typed without pulling in unstable libdom) ---
type HighlightRegistry = { set(name: string, hl: object): void; delete(name: string): void };
type HighlightCtor = new (...ranges: Range[]) => object;

function registry(): HighlightRegistry | null {
  return (CSS as unknown as { highlights?: HighlightRegistry }).highlights ?? null;
}
function makeHighlight(ranges: Range[]): object | null {
  const Ctor = (window as unknown as { Highlight?: HighlightCtor }).Highlight;
  return Ctor ? new Ctor(...ranges) : null;
}
function isSupported(): boolean {
  return (
    typeof window !== "undefined" && "Highlight" in window && registry() !== null
  );
}

function storageKey(testId: number | string) {
  return `reading-${testId}-highlights`;
}

/** char offset of a DOM point within paraEl's displayed text. */
function pointOffset(paraEl: Element, node: Node, nodeOffset: number): number {
  const r = document.createRange();
  r.selectNodeContents(paraEl);
  try {
    r.setEnd(node, nodeOffset);
  } catch {
    return 0;
  }
  return r.toString().length;
}

/** Range spanning [start, end) chars of paraEl's displayed text. */
function rangeFromOffsets(paraEl: Element, start: number, end: number): Range | null {
  const walker = document.createTreeWalker(paraEl, NodeFilter.SHOW_TEXT);
  const range = document.createRange();
  let pos = 0;
  let startSet = false;
  let node = walker.nextNode();
  while (node) {
    const len = node.textContent?.length ?? 0;
    if (!startSet && start <= pos + len) {
      range.setStart(node, Math.max(0, start - pos));
      startSet = true;
    }
    if (startSet && end <= pos + len) {
      range.setEnd(node, Math.max(0, end - pos));
      return range;
    }
    pos += len;
    node = walker.nextNode();
  }
  return startSet ? range : null;
}

function paraOf(node: Node): HTMLElement | null {
  const el = node.nodeType === Node.ELEMENT_NODE ? (node as Element) : node.parentElement;
  return (el?.closest("[data-hl-para]") as HTMLElement | null) ?? null;
}

/**
 * Multi-colour reading highlighter. Pick a colour, then select passage text to
 * paint it; the eraser removes highlights under the selection. Highlights are
 * rendered with the CSS Custom Highlight API (no DOM mutation, so it never fights
 * React) and persisted per test in localStorage.
 */
export function PassageHighlighter({
  testId,
  passage,
  brush,
  onBrush,
}: {
  testId: number | string;
  passage: number;
  brush: Brush;
  onBrush: (b: Brush) => void;
}) {
  const [ok, setOk] = useState(false);
  const [marks, setMarks] = useState<Mark[]>(() => {
    if (typeof window === "undefined") return [];
    try {
      const raw = localStorage.getItem(storageKey(testId));
      return raw ? (JSON.parse(raw) as Mark[]) : [];
    } catch {
      return [];
    }
  });
  useEffect(() => {
    // Deferred so the client-only support flag flips after hydration (not
    // synchronously in the effect body).
    const t = window.setTimeout(() => setOk(isSupported()), 0);
    return () => window.clearTimeout(t);
  }, []);

  // Persist on change.
  useEffect(() => {
    try {
      localStorage.setItem(storageKey(testId), JSON.stringify(marks));
    } catch {
      /* storage full / disabled — highlighting still works this session */
    }
  }, [marks, testId]);

  // Rebuild the highlight registries for the current passage.
  const rebuild = useCallback(() => {
    const reg = registry();
    if (!reg) return;
    const byColor: Record<HlColor, Range[]> = { yellow: [], green: [], pink: [], blue: [] };
    for (const m of marks) {
      if (m.passage !== passage) continue;
      const paraEl = document.querySelector(`[data-hl-para="${m.para}"]`);
      if (!paraEl) continue;
      const r = rangeFromOffsets(paraEl, m.start, m.end);
      if (r) byColor[m.color].push(r);
    }
    for (const c of ALL_COLORS) {
      const name = `hl-${c}`;
      const hl = byColor[c].length ? makeHighlight(byColor[c]) : null;
      if (hl) reg.set(name, hl);
      else reg.delete(name);
    }
  }, [marks, passage]);

  useEffect(() => {
    if (!ok) return;
    const id = requestAnimationFrame(rebuild);
    return () => cancelAnimationFrame(id);
  }, [ok, rebuild]);

  // Clear registries on unmount.
  useEffect(() => {
    return () => {
      const reg = registry();
      if (reg) ALL_COLORS.forEach((c) => reg.delete(`hl-${c}`));
    };
  }, []);

  // Paint / erase on selection when a brush is active.
  useEffect(() => {
    if (!ok) return;
    const onUp = () =>
      window.setTimeout(() => {
        const b = brush;
        if (!b) return;
        const sel = window.getSelection();
        if (!sel || sel.isCollapsed || sel.rangeCount === 0) return;
        const range = sel.getRangeAt(0);
        const startPara = paraOf(range.startContainer);
        if (!startPara || paraOf(range.endContainer) !== startPara) return;
        const para = Number(startPara.dataset.hlPara);
        const start = pointOffset(startPara, range.startContainer, range.startOffset);
        const end = pointOffset(startPara, range.endContainer, range.endOffset);
        if (end <= start) return;
        sel.removeAllRanges();
        const overlaps = (m: Mark) =>
          m.passage === passage && m.para === para && m.start < end && m.end > start;
        if (b === "eraser") {
          setMarks((prev) => prev.filter((m) => !overlaps(m)));
        } else {
          setMarks((prev) => [
            ...prev.filter((m) => !(overlaps(m) && m.color === b)),
            { passage, para, start, end, color: b },
          ]);
        }
      }, 0);
    document.addEventListener("mouseup", onUp);
    return () => document.removeEventListener("mouseup", onUp);
  }, [ok, passage, brush]);

  if (!ok) return null;

  const hasMarks = marks.some((m) => m.passage === passage);

  return (
    <div className="pointer-events-none fixed inset-x-0 bottom-4 z-40 flex justify-center px-4">
      <div className="pointer-events-auto flex items-center gap-1.5 rounded-full border border-slate-200 bg-white/95 px-2.5 py-1.5 shadow-lg backdrop-blur">
        <Highlighter className="h-4 w-4 text-slate-400" />
        {COLORS.map((c) => (
          <button
            key={c.key}
            type="button"
            title={c.label}
            aria-pressed={brush === c.key}
            onClick={() => onBrush(brush === c.key ? null : c.key)}
            className={`h-6 w-6 rounded-full ${c.swatch} transition ${
              brush === c.key
                ? "ring-2 ring-slate-900 ring-offset-1"
                : "hover:scale-110"
            }`}
          />
        ))}
        <button
          type="button"
          title="Eraser"
          aria-pressed={brush === "eraser"}
          onClick={() => onBrush(brush === "eraser" ? null : "eraser")}
          className={`flex h-6 w-6 items-center justify-center rounded-full transition ${
            brush === "eraser" ? "bg-slate-900 text-white" : "text-slate-500 hover:bg-slate-100"
          }`}
        >
          <Eraser className="h-3.5 w-3.5" />
        </button>
        {hasMarks && (
          <button
            type="button"
            title="Clear highlights on this passage"
            onClick={() => setMarks((prev) => prev.filter((m) => m.passage !== passage))}
            className="flex h-6 items-center gap-1 rounded-full px-2 text-xs font-medium text-slate-500 transition hover:bg-slate-100"
          >
            <X className="h-3.5 w-3.5" /> Clear
          </button>
        )}
      </div>
    </div>
  );
}
