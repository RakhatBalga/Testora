"use client";

import { X, CheckCircle2, Circle, Flag, AlertTriangle } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { QuestionPalette, type PaletteItem } from "./QuestionPalette";

/**
 * Review screen shown before submission: counts of answered / unanswered /
 * marked questions, the full palette to jump back, and a final submit
 * confirmation. Doubles as the submit-confirmation modal.
 */
export function ReviewModal({
  open,
  items,
  currentId,
  submitting,
  timeUp,
  onJump,
  onClose,
  onSubmit,
}: {
  open: boolean;
  items: PaletteItem[];
  currentId: number | null;
  submitting: boolean;
  timeUp: boolean;
  onJump: (id: number) => void;
  onClose: () => void;
  onSubmit: () => void;
}) {
  if (!open) return null;

  const answered = items.filter((i) => i.answered).length;
  const unanswered = items.length - answered;
  const marked = items.filter((i) => i.marked).length;

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-slate-900/40 p-0 backdrop-blur-sm sm:items-center sm:p-4">
      <div className="flex max-h-[90vh] w-full max-w-xl flex-col overflow-hidden rounded-t-3xl bg-white shadow-2xl sm:rounded-3xl">
        <div className="flex items-center justify-between border-b border-[var(--border)] px-6 py-4">
          <h2 className="text-base font-semibold text-[var(--text-primary)]">Review your answers</h2>
          {!timeUp && (
            <button
              type="button"
              onClick={onClose}
              className="rounded-lg p-1 text-slate-400 transition hover:bg-slate-100 hover:text-slate-600"
              aria-label="Close review"
            >
              <X className="h-5 w-5" />
            </button>
          )}
        </div>

        <div className="space-y-5 overflow-y-auto px-6 py-5">
          {timeUp && (
            <div className="flex items-center gap-2 rounded-xl bg-amber-50 px-4 py-3 text-sm font-medium text-amber-700">
              <AlertTriangle className="h-4 w-4 flex-shrink-0" />
              Time is up — submit your test to see your results.
            </div>
          )}

          <div className="grid grid-cols-3 gap-3">
            <Stat icon={<CheckCircle2 className="h-4 w-4" />} value={answered} label="Answered" tone="text-emerald-600" />
            <Stat icon={<Circle className="h-4 w-4" />} value={unanswered} label="Unanswered" tone="text-slate-500" />
            <Stat icon={<Flag className="h-4 w-4" />} value={marked} label="Marked" tone="text-amber-500" />
          </div>

          {unanswered > 0 && !timeUp && (
            <p className="text-sm text-[var(--text-secondary)]">
              You still have <strong className="text-[var(--text-primary)]">{unanswered}</strong>{" "}
              unanswered {unanswered === 1 ? "question" : "questions"}. Tap a number to go back.
            </p>
          )}

          <QuestionPalette items={items} currentId={currentId} onJump={(id) => { onJump(id); onClose(); }} />
        </div>

        <div className="flex gap-3 border-t border-[var(--border)] px-6 py-4">
          {!timeUp && (
            <Button variant="secondary" onClick={onClose} className="flex-1">
              Keep working
            </Button>
          )}
          <Button onClick={onSubmit} disabled={submitting} className="flex-1">
            {submitting ? "Submitting…" : "Submit test"}
          </Button>
        </div>
      </div>
    </div>
  );
}

function Stat({
  icon,
  value,
  label,
  tone,
}: {
  icon: React.ReactNode;
  value: number;
  label: string;
  tone: string;
}) {
  return (
    <div className="rounded-2xl border border-[var(--border)] p-3 text-center">
      <span className={`inline-flex ${tone}`}>{icon}</span>
      <p className="mt-1 text-2xl font-extrabold text-[var(--text-primary)]">{value}</p>
      <p className="text-[0.7rem] font-medium uppercase tracking-wide text-[var(--text-secondary)]">{label}</p>
    </div>
  );
}
