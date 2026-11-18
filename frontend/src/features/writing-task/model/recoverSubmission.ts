import type { WritingSubmissionSummary } from "@/shared/api";

/** Client and server clocks may disagree; only used when no snapshot exists. */
const CLOCK_SKEW_MS = 120_000;

export type SubmitAttempt = {
  taskId: number;
  /** Submission ids for this task seen before submitting, or null if unknown. */
  knownIds: ReadonlySet<number> | null;
  /** Date.now() when the submit request was sent. */
  startedAt: number;
};

// API timestamps are UTC, including responses without an explicit offset.
function serverTime(stamp: string): number {
  return Date.parse(/[Zz]|[+-]\d\d:\d\d$/.test(stamp) ? stamp : `${stamp}Z`);
}

/**
 * After a submit request ended without an answer (timeout, dropped connection),
 * find the submission the server created for it. The server keeps grading a
 * request the browser gave up on, so resubmitting blindly would review the same
 * essay twice. Returns null when the essay never reached the server.
 */
export function findSubmittedWriting(
  submissions: WritingSubmissionSummary[],
  attempt: SubmitAttempt,
): WritingSubmissionSummary | null {
  const created = submissions.filter((item) => {
    if (item.task_id !== attempt.taskId) return false;
    if (attempt.knownIds) return !attempt.knownIds.has(item.id);
    return serverTime(item.created_at) >= attempt.startedAt - CLOCK_SKEW_MS;
  });
  return created.reduce<WritingSubmissionSummary | null>(
    (latest, item) => (latest === null || item.id > latest.id ? item : latest),
    null,
  );
}
