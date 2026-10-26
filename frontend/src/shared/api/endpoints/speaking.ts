import { request, requestForm, requestFormWithProgress, audioFilename } from "../http";
import type { FreeQuota, SpeakingSubmission, SpeakingSubmissionSummary, SpeakingTask } from "../types";

export const speakingApi = {
  getSpeakingQuota: () => request<FreeQuota>("/speaking/quota"),

  listSpeakingTasks: () => request<SpeakingTask[]>("/speaking/tasks"),

  getSpeakingTask: (id: number) => request<SpeakingTask>(`/speaking/tasks/${id}`),

  submitSpeaking: (task_id: number, audio: Blob, onProgress?: (percent: number) => void) => {
    const formData = new FormData();
    formData.append("task_id", String(task_id));
    formData.append("audio", audio, audioFilename(audio));
    return onProgress
      ? requestFormWithProgress<SpeakingSubmission>("/speaking/submit", formData, onProgress)
      : requestForm<SpeakingSubmission>("/speaking/submit", formData);
  },

  listSpeakingSubmissions: () =>
    request<SpeakingSubmissionSummary[]>("/speaking/submissions"),

  getSpeakingSubmission: (id: number) =>
    request<SpeakingSubmission>(`/speaking/submissions/${id}`),
};
