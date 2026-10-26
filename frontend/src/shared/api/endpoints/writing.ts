import { request } from "../http";

/** Grading runs inside the request. A slow self-hosted Qwen needs ~1.5-3 min per essay
 *  (examiner + coach calls, each capped at QWEN_TIMEOUT_SECONDS = 180 s on the server),
 *  so allow both stages plus slack. A request that still times out is not lost: the
 *  server finishes it and the submission shows up in /writing/submissions. */
export const WRITING_GRADING_TIMEOUT_MS = 420_000;
import type { FreeQuota, WritingSubmission, WritingSubmissionSummary, WritingTask } from "../types";

export const writingApi = {
  listWritingTasks: () => request<WritingTask[]>("/writing/tasks"),

  getWritingTask: (id: number) => request<WritingTask>(`/writing/tasks/${id}`),

  getWritingQuota: () => request<FreeQuota>("/writing/quota"),

  submitWriting: (task_id: number, text: string) =>
    request<WritingSubmission>("/writing/submit", {
      method: "POST",
      body: JSON.stringify({ task_id, text }),
    }, { timeoutMs: WRITING_GRADING_TIMEOUT_MS }),

  listWritingSubmissions: () =>
    request<WritingSubmissionSummary[]>("/writing/submissions"),

  getWritingSubmission: (id: number) =>
    request<WritingSubmission>(`/writing/submissions/${id}`),

  retryWritingSubmission: (id: number) =>
    request<WritingSubmission>(`/writing/submissions/${id}/retry`, {
      method: "POST",
    }, { timeoutMs: WRITING_GRADING_TIMEOUT_MS }),
};
