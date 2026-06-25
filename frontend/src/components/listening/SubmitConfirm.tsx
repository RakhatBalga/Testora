import { AlertTriangle, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/Button";

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
  if (!open) return null;
  const remaining = total - answered;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 p-4">
      <div className="w-full max-w-md rounded-2xl bg-white p-6 shadow-xl">
        <div className="flex items-start gap-3">
          <span className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-full bg-amber-50 text-amber-600">
            <AlertTriangle className="h-5 w-5" />
          </span>
          <div>
            <h3 className="text-lg font-bold text-slate-900">Submit your answers?</h3>
            <p className="mt-1 text-sm text-slate-600">
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
