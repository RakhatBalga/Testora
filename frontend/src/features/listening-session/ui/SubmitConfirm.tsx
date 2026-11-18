"use client";

import { useEffect, useRef } from "react";
import { AlertTriangle, Loader2 } from "lucide-react";
import { Button } from "@/shared/ui";

type Props = {
  open: boolean;
  answered: number;
  total: number;
  submitting: boolean;
  onConfirm: () => void;
  onCancel: () => void;
};

/** Confirmation dialog before final submission. Surfaces how many questions
 *  are still unanswered so the user can go back if it was accidental. */
export function SubmitConfirm({ open, answered, total, submitting, onConfirm, onCancel }: Props) {
  const panelRef = useRef<HTMLDivElement>(null);
  const cancelRef = useRef(onCancel);
  const submittingRef = useRef(submitting);

  useEffect(() => {
    cancelRef.current = onCancel;
    submittingRef.current = submitting;
  });

  // Modal behaviour: focus moves into the dialog, Tab stays inside it, Escape
  // cancels, and focus returns to where it was when the dialog closes.
  useEffect(() => {
    if (!open) return;
    const previous = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    const focusable = () =>
      Array.from(panelRef.current?.querySelectorAll<HTMLElement>("button:not([disabled])") ?? []);
    (focusable()[0] ?? panelRef.current)?.focus();

    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        if (!submittingRef.current) cancelRef.current();
        return;
      }
      if (event.key !== "Tab") return;
      const items = focusable();
      if (items.length === 0) {
        event.preventDefault();
        panelRef.current?.focus();
        return;
      }
      const first = items[0];
      const last = items[items.length - 1];
      const active = document.activeElement;
      const inside = active instanceof Node && panelRef.current?.contains(active);
      if (event.shiftKey && (active === first || !inside)) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && (active === last || !inside)) {
        event.preventDefault();
        first.focus();
      }
    };
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("keydown", onKeyDown);
      previous?.focus();
    };
  }, [open]);

  if (!open) return null;
  const remaining = total - answered;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 p-4">
      <div
        ref={panelRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="submit-confirm-title"
        aria-describedby="submit-confirm-detail"
        tabIndex={-1}
        className="w-full max-w-md rounded-2xl bg-white p-6 shadow-xl outline-none"
      >
        <div className="flex items-start gap-3">
          <span className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-full bg-amber-50 text-amber-600">
            <AlertTriangle className="h-5 w-5" />
          </span>
          <div>
            <h3 id="submit-confirm-title" className="text-lg font-bold text-slate-900">Submit your answers?</h3>
            <p id="submit-confirm-detail" className="mt-1 text-sm text-slate-600">
              You have answered <strong>{answered}</strong> of <strong>{total}</strong> questions.
              {remaining > 0 && (
                <>
                  {" "}
                  <span className="text-amber-700">{remaining} still unanswered.</span>
                </>
              )}{" "}
              You can&apos;t change your answers after submitting.
            </p>
          </div>
        </div>
        <div className="mt-6 flex justify-end gap-2">
          <Button variant="secondary" onClick={onCancel} disabled={submitting}>
            Keep working
          </Button>
          <Button onClick={onConfirm} disabled={submitting}>
            {submitting ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
            Submit now
          </Button>
        </div>
      </div>
    </div>
  );
}
