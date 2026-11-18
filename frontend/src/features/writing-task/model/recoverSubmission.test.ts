import { expect, it } from "vitest";
import type { WritingSubmissionSummary } from "@/shared/api";
import { findSubmittedWriting } from "./recoverSubmission";

const STARTED = Date.parse("2026-11-18T10:00:00Z");

function submission(id: number, overrides: Partial<WritingSubmissionSummary> = {}): WritingSubmissionSummary {
  return { id, task_id: 3, task_title: "Task", word_count: 260, status: "graded", band: 6.5,
    created_at: "2026-11-18T10:00:05", ...overrides };
}

it("finds the submission created after the snapshot, pending or graded", () => {
  const attempt = { taskId: 3, knownIds: new Set([10]), startedAt: STARTED };
  expect(findSubmittedWriting([submission(11, { status: "pending", band: null }), submission(10)], attempt)?.id).toBe(11);
  expect(findSubmittedWriting([submission(12), submission(10)], attempt)?.id).toBe(12);
});

it("returns null when nothing new exists, so a retry is safe", () => {
  const attempt = { taskId: 3, knownIds: new Set([10]), startedAt: STARTED };
  expect(findSubmittedWriting([submission(10)], attempt)).toBeNull();
  expect(findSubmittedWriting([], attempt)).toBeNull();
});

it("ignores submissions for other tasks", () => {
  const attempt = { taskId: 3, knownIds: new Set<number>(), startedAt: STARTED };
  expect(findSubmittedWriting([submission(11, { task_id: 4 })], attempt)).toBeNull();
});

it("falls back to the creation time when there is no snapshot", () => {
  const attempt = { taskId: 3, knownIds: null, startedAt: STARTED };
  const old = submission(10, { created_at: "2026-11-18T09:30:00" });
  expect(findSubmittedWriting([old], attempt)).toBeNull();
  // Timestamps without an offset are UTC; a small clock difference is tolerated.
  expect(findSubmittedWriting([submission(11, { created_at: "2026-11-18T09:59:30" }), old], attempt)?.id).toBe(11);
  expect(findSubmittedWriting([submission(12, { created_at: "2026-11-18T10:03:00Z" }), old], attempt)?.id).toBe(12);
});
