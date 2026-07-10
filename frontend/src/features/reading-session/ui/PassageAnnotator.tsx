"use client";

import { useCallback, useEffect, useState } from "react";
import { BookmarkPlus, Check, Trash2 } from "lucide-react";
import { api } from "@/shared/api";

type HlColor = "yellow" | "green" | "pink" | "blue";
type Mark = {
  passage: number;
  para: number;
  start: number;
  end: number;
  bg: HlColor | null;
  text: HlColor | null;
};
type Anchor = {
  top: number;
  left: number;
  para: number;
  start: number;
  end: number;
  text: string;
  context: string;
};
type SaveState = "idle" | "saving" | "saved" | "error";

const ALL: HlColor[] = ["yellow", "green", "pink", "blue"];
const BG_SWATCH: Record<HlColor, string> = {
  yellow: "bg-yellow-300",
  green: "bg-green-300",
  pink: "bg-pink-300",
  blue: "bg-blue-300",
};
const TEXT_SWATCH: Record<HlColor, string> = {
  yellow: "text-yellow-600",
  green: "text-green-600",
  pink: "text-pink-600",
  blue: "text-blue-600",
};

// --- CSS Custom Highlight API (typed without pulling in unstable libdom) ---
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
  return typeof window !== "undefined" && "Highlight" in window && registry() !== null;
}

function storageKey(testId: number | string) {
  return `reading-${testId}-highlights`;
}
function loadMarks(testId: number | string): Mark[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = localStorage.getItem(storageKey(testId));
    return raw ? (JSON.parse(raw) as Mark[]) : [];
  } catch {
    return [];
  }
}

function sentenceAround(container: string, word: string): string {
  const parts = container.split(/(?<=[.!?])\s+/);
  const hit = parts.find((s) => s.toLowerCase().includes(word.toLowerCase()));
  return (hit || container).trim().slice(0, 1000);
}

function paraOf(node: Node): HTMLElement | null {
  const el = node.nodeType === Node.ELEMENT_NODE ? (node as Element) : node.parentElement;
  return (el?.closest("[data-hl-para]") as HTMLElement | null) ?? null;
}
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

/**
 * Reading-passage annotation menu. Selecting text pops a small menu to paint a
 * fill colour and/or a text colour (a colour can't be used for both at once, so
 * text stays readable), remove the highlight under the selection, or save the
 * word. Highlights render via the CSS Custom Highlight API (no DOM mutation) and
 * persist per test in localStorage.
 */
export function PassageAnnotator({
  testId,
  passage,
  sourceRef,
}: {
  testId: number | string;
  passage: number;
  sourceRef?: string;
}) {
  const [ok, setOk] = useState(false);
  const [marks, setMarks] = useState<Mark[]>(() => loadMarks(testId));
  const [anchor, setAnchor] = useState<Anchor | null>(null);
  const [saveState, setSaveState] = useState<SaveState>("idle");

  useEffect(() => {
    const t = window.setTimeout(() => setOk(isSupported()), 0);
    return () => window.clearTimeout(t);
  }, []);

  useEffect(() => {
    try {
      localStorage.setItem(storageKey(testId), JSON.stringify(marks));
    } catch {
      /* storage disabled — highlighting still works this session */
    }
  }, [marks, testId]);

  const rebuild = useCallback(() => {
    const reg = registry();
    if (!reg) return;
    const bg: Record<HlColor, Range[]> = { yellow: [], green: [], pink: [], blue: [] };
    const text: Record<HlColor, Range[]> = { yellow: [], green: [], pink: [], blue: [] };
    for (const m of marks) {
      if (m.passage !== passage) continue;
      const paraEl = document.querySelector(`[data-hl-para="${m.para}"]`);
      if (!paraEl) continue;
      const r = rangeFromOffsets(paraEl, m.start, m.end);
      if (!r) continue;
      if (m.bg) bg[m.bg].push(r);
      if (m.text) text[m.text].push(r.cloneRange());
    }
    for (const c of ALL) {
      const bgName = `hl-bg-${c}`;
      const bgHl = bg[c].length ? makeHighlight(bg[c]) : null;
      if (bgHl) reg.set(bgName, bgHl);
      else reg.delete(bgName);
      const textName = `hl-text-${c}`;
      const textHl = text[c].length ? makeHighlight(text[c]) : null;
      if (textHl) reg.set(textName, textHl);
      else reg.delete(textName);
    }
  }, [marks, passage]);

  useEffect(() => {
    if (!ok) return;
    const id = requestAnimationFrame(rebuild);
    return () => cancelAnimationFrame(id);
  }, [ok, rebuild]);

  useEffect(() => {
    return () => {
      const reg = registry();
      if (reg)
        ALL.forEach((c) => {
          reg.delete(`hl-bg-${c}`);
          reg.delete(`hl-text-${c}`);
        });
    };
  }, []);

  // Selection -> show the annotation menu.
  useEffect(() => {
    if (!ok) return;
    const onUp = () =>
      window.setTimeout(() => {
        const sel = window.getSelection();
        if (!sel || sel.isCollapsed || sel.rangeCount === 0) return;
        const range = sel.getRangeAt(0);
        const startPara = paraOf(range.startContainer);
        if (!startPara || paraOf(range.endContainer) !== startPara) {
          setAnchor(null);
          return;
        }
        const para = Number(startPara.dataset.hlPara);
        const start = pointOffset(startPara, range.startContainer, range.startOffset);
        const end = pointOffset(startPara, range.endContainer, range.endOffset);
        if (end <= start) {
          setAnchor(null);
          return;
        }
        const text = sel.toString().trim().replace(/\s+/g, " ");
        const context = sentenceAround(
          (startPara.textContent ?? "").replace(/\s+/g, " ").trim(),
          text,
        );
        const rect = range.getBoundingClientRect();
        setAnchor({
          top: rect.top - 8,
          left: rect.left + rect.width / 2,
          para,
          start,
          end,
          text,
          context,
        });
        setSaveState("idle");
      }, 0);
    const onDown = (e: MouseEvent) => {
      if ((e.target as Element)?.closest?.("[data-annot-menu]")) return;
      setAnchor(null);
    };
    const onScroll = () => setAnchor(null);
    document.addEventListener("mouseup", onUp);
    document.addEventListener("mousedown", onDown);
    window.addEventListener("scroll", onScroll, true);
    return () => {
      document.removeEventListener("mouseup", onUp);
      document.removeEventListener("mousedown", onDown);
      window.removeEventListener("scroll", onScroll, true);
    };
  }, [ok]);

  const current = anchor
    ? marks.find(
        (m) =>
          m.passage === passage &&
          m.para === anchor.para &&
          m.start === anchor.start &&
          m.end === anchor.end,
      )
    : undefined;

  const applyColor = (kind: "bg" | "text", color: HlColor) => {
    if (!anchor) return;
    setMarks((prev) => {
      const idx = prev.findIndex(
        (m) =>
          m.passage === passage &&
          m.para === anchor.para &&
          m.start === anchor.start &&
          m.end === anchor.end,
      );
      const base: Mark =
        idx >= 0
          ? prev[idx]
          : {
              passage,
              para: anchor.para,
              start: anchor.start,
              end: anchor.end,
              bg: null,
              text: null,
            };
      // Toggle off if the same colour is re-picked.
      const nextVal = base[kind] === color ? null : color;
      const updated: Mark = { ...base, [kind]: nextVal };
      // Keep fill and text colours distinct so text stays readable.
      if (updated.bg && updated.text && updated.bg === updated.text) {
        if (kind === "bg") updated.text = null;
        else updated.bg = null;
      }
      const next = idx >= 0 ? [...prev.slice(0, idx), updated, ...prev.slice(idx + 1)] : [...prev, updated];
      // Drop marks with no styling left.
      return next.filter((m) => m.bg || m.text);
    });
    // Clear the native (blue) selection so the applied colour is what's shown.
    // The menu stays open (anchored offsets persist) so a text colour can follow.
    window.getSelection()?.removeAllRanges();
  };

  const removeSelection = () => {
    if (!anchor) return;
    const { para, start, end } = anchor;
    setMarks((prev) =>
      prev.filter(
        (m) => !(m.passage === passage && m.para === para && m.start < end && m.end > start),
      ),
    );
    setAnchor(null);
    window.getSelection()?.removeAllRanges();
  };

  const saveWord = async () => {
    if (!anchor) return;
    setSaveState("saving");
    try {
      await api.saveWord({
        word: anchor.text,
        context: anchor.context,
        source: "reading",
        source_ref: sourceRef,
      });
      setSaveState("saved");
      window.setTimeout(() => setAnchor(null), 800);
    } catch {
      setSaveState("error");
    }
  };

  if (!ok || !anchor) return null;

  const overlapsMark = marks.some(
    (m) =>
      m.passage === passage &&
      m.para === anchor.para &&
      m.start < anchor.end &&
      m.end > anchor.start,
  );
  const isWord =
    anchor.text.length <= 60 && anchor.text.split(/\s+/).length <= 4 && /[A-Za-z]/.test(anchor.text);

  return (
    <div
      data-annot-menu
      onMouseDown={(e) => e.preventDefault()}
      className="fixed z-50 -translate-x-1/2 -translate-y-full"
      style={{ top: anchor.top, left: anchor.left }}
    >
      <div className="flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-2.5 py-1.5 shadow-lg">
        <div className="flex items-center gap-1" title="Fill">
          {ALL.map((c) => (
            <button
              key={`bg-${c}`}
              type="button"
              onClick={() => applyColor("bg", c)}
              aria-pressed={current?.bg === c}
              title={`Fill ${c}`}
              className={`h-5 w-5 rounded-full ${BG_SWATCH[c]} transition ${
                current?.bg === c ? "ring-2 ring-slate-900 ring-offset-1" : "hover:scale-110"
              }`}
            />
          ))}
        </div>

        <span className="h-5 w-px bg-slate-200" />

        <div className="flex items-center gap-0.5" title="Text colour">
          {ALL.map((c) => {
            const disabled = current?.bg === c;
            return (
              <button
                key={`text-${c}`}
                type="button"
                disabled={disabled}
                onClick={() => applyColor("text", c)}
                aria-pressed={current?.text === c}
                title={disabled ? "Same as fill" : `Text ${c}`}
                className={`flex h-5 w-5 items-center justify-center rounded text-sm font-bold ${TEXT_SWATCH[c]} transition ${
                  current?.text === c ? "ring-2 ring-slate-900" : "hover:bg-slate-100"
                } ${disabled ? "cursor-not-allowed opacity-30" : ""}`}
              >
                A
              </button>
            );
          })}
        </div>

        {overlapsMark && (
          <>
            <span className="h-5 w-px bg-slate-200" />
            <button
              type="button"
              onClick={removeSelection}
              title="Remove highlight"
              className="flex h-6 w-6 items-center justify-center rounded-lg text-slate-500 transition hover:bg-red-50 hover:text-red-500"
            >
              <Trash2 className="h-4 w-4" />
            </button>
          </>
        )}

        {isWord && (
          <>
            <span className="h-5 w-px bg-slate-200" />
            <button
              type="button"
              onClick={saveWord}
              disabled={saveState === "saving"}
              className="flex items-center gap-1 rounded-lg bg-slate-900 px-2 py-1 text-xs font-semibold text-white transition hover:bg-slate-800 disabled:opacity-70"
            >
              {saveState === "saved" ? (
                <>
                  <Check className="h-3.5 w-3.5" /> Saved
                </>
              ) : (
                <>
                  <BookmarkPlus className="h-3.5 w-3.5" />
                  {saveState === "error" ? "Retry" : "Save"}
                </>
              )}
            </button>
          </>
        )}
      </div>
    </div>
  );
}
