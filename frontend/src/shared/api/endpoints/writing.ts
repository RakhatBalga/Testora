import { request } from "../http";
import type { FreeQuota, WritingSubmission, WritingSubmissionSummary, WritingTask } from "../types";

export const writingApi = {
  listWritingTasks: () => request<WritingTask[]>("/writing/tasks"),

  getWritingTask: (id: number) => request<WritingTask>(`/writing/tasks/${id}`),

  getWritingQuota: () => request<FreeQuota>("/writing/quota"),

  submitWriting: (task_id: number, text: string) =>
    request<WritingSubmission>("/writing/submit", {
      method: "POST",
      body: JSON.stringify({ task_id, text }),
    }),

  listWritingSubmissions: () =>
    request<WritingSubmissionSummary[]>("/writing/submissions"),

  getWritingSubmission: (id: number) =>
    request<WritingSubmission>(`/writing/submissions/${id}`),

  retryWritingSubmission: (id: number) =>
    request<WritingSubmission>(`/writing/submissions/${id}/retry`, {
      method: "POST",
    }),
};
