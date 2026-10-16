"use client";

import { useRef, useState } from "react";
import { Button, Card } from "@/shared/ui";

export function reviewState(submission: { status?: string; band: number | null; feedback: unknown }) {
  if (submission.status === "pending") return "pending";
  if (submission.status === "failed") return "failed";
  if (submission.band !== null) return "graded";
  return submission.feedback ? "failed" : "pending";
}

export function ReviewStatusNotice({ state, onRefresh }: {
  state: "pending" | "failed";
  onRefresh: () => Promise<void>;
}) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const inFlight = useRef(false);
  const refresh = async () => {
    if (inFlight.current) return;
    inFlight.current = true;
    setBusy(true);
    setError("");
    try { await onRefresh(); }
    catch (err) { setError(err instanceof Error ? err.message : "Could not check the review status."); }
    finally { inFlight.current = false; setBusy(false); }
  };
  return (
    <Card className="space-y-3 p-6">
      <h2 className="font-semibold text-slate-900">
        {state === "pending" ? "Review not completed yet" : "Review could not be completed"}
      </h2>
      <p role="status" className="text-sm text-slate-600">
        {state === "pending"
          ? "Your response is saved. The review may still be running or may have been interrupted. Check its status before submitting again."
          : "Your response is saved, but no score was produced. You can return to the task to try again."}
      </p>
      {state === "pending" && <p className="text-sm text-slate-600">If the status does not change, contact support with the result page link.</p>}
      {error && <p role="alert" className="text-sm text-red-600">{error}</p>}
      <Button onClick={refresh} disabled={busy}>{busy ? "Checking..." : "Check review status"}</Button>
      <p className="text-xs text-slate-500">Checking the status does not start another AI review.</p>
    </Card>
  );
}
