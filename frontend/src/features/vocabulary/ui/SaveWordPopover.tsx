"use client";

import { useCallback, useEffect, useState } from "react";
import { BookmarkPlus, Check } from "lucide-react";
import { api } from "@/shared/api";

type Anchor = { text: string; context: string; top: number; left: number };
type SaveState = "idle" | "saving" | "saved" | "error";

/** Return the sentence in `container` that contains `word` (fallback: the whole text). */
function sentenceAround(container: string, word: string): string {
  const parts = container.split(/(?<=[.!?])\s+/);
  const hit = parts.find((s) => s.toLowerCase().includes(word.toLowerCase()));
  return (hit || container).trim().slice(0, 1000);
}

/**
 * Floating "Save word" affordance. Listens for a text selection made inside any
 * element marked `data-vocab-selectable` (e.g. a reading passage) and offers to
 * save the selected word together with the sentence it came from.
 */
export function SaveWordPopover({
  source = "reading",
  sourceRef,
  onSaved,
}: {
  source?: string;
  sourceRef?: string;
  /** Called with the saved word after a successful save (e.g. to highlight it). */
  onSaved?: (word: string) => void;
}) {
  const [anchor, setAnchor] = useState<Anchor | null>(null);
  const [state, setState] = useState<SaveState>("idle");

  const capture = useCallback(() => {
    const sel = window.getSelection();
    if (!sel || sel.isCollapsed) {
      setAnchor(null);
      return;
    }
    const text = sel.toString().trim().replace(/\s+/g, " ");
    // Single word or short phrase only — not whole sentences/paragraphs.
    if (!text || text.length > 60 || !/[A-Za-z]/.test(text) || text.split(/\s+/).length > 4) {
      setAnchor(null);
      return;
    }
    const range = sel.getRangeAt(0);
    const node = range.commonAncestorContainer;
    const el =
      node.nodeType === Node.ELEMENT_NODE ? (node as Element) : node.parentElement;
    const region = el?.closest("[data-vocab-selectable]");
    if (!region) {
      setAnchor(null);
      return;
    }
    const para = el?.closest("p") ?? region;
    const context = sentenceAround(
      (para.textContent ?? "").replace(/\s+/g, " ").trim(),
      text,
    );
    const rect = range.getBoundingClientRect();
    setAnchor({ text, context, top: rect.top - 8, left: rect.left + rect.width / 2 });
    setState("idle");
  }, []);

  useEffect(() => {
    // setTimeout(0) lets the selection settle after mouseup before we read it.
    const onUp = () => window.setTimeout(capture, 0);
    const onDown = (e: MouseEvent) => {
      if ((e.target as Element)?.closest?.("[data-vocab-popover]")) return;
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
  }, [capture]);

  const save = async () => {
    if (!anchor) return;
    setState("saving");
    try {
      await api.saveWord({
        word: anchor.text,
        context: anchor.context,
        source,
        source_ref: sourceRef,
      });
      onSaved?.(anchor.text);
      setState("saved");
      window.getSelection()?.removeAllRanges();
      window.setTimeout(() => setAnchor(null), 900);
    } catch {
      setState("error");
    }
  };

  if (!anchor) return null;

  return (
    <div
      data-vocab-popover
      className="fixed z-50 -translate-x-1/2 -translate-y-full"
      style={{ top: anchor.top, left: anchor.left }}
    >
      <button
        type="button"
        // Keep the text selection alive through the click.
        onMouseDown={(e) => e.preventDefault()}
        onClick={save}
        disabled={state === "saving"}
        className="flex items-center gap-1.5 rounded-lg bg-slate-900 px-3 py-1.5 text-xs font-semibold text-white shadow-lg transition hover:bg-slate-800 disabled:opacity-70"
      >
        {state === "saved" ? (
          <>
            <Check className="h-3.5 w-3.5" /> Saved
          </>
        ) : (
          <>
            <BookmarkPlus className="h-3.5 w-3.5" />
            {state === "error" ? "Retry" : state === "saving" ? "Saving…" : "Save word"}
          </>
        )}
      </button>
    </div>
  );
}
