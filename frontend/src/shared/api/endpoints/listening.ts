import { request, queryString } from "../http";
import type { AnswerValue, ListeningCatalogItem, ListeningMode, ListeningProgress, ListeningReview, ListeningSubmitResult, ListeningTest } from "../types";

export const listeningApi = {
  listListeningTests: () => request<ListeningCatalogItem[]>("/listening/tests"),

  getListeningTest: (id: number) => request<ListeningTest>(`/listening/tests/${id}`),

  getListeningProgress: (id: number, content_version: string, mode: ListeningMode) =>
    request<ListeningProgress | null>(`/listening/tests/${id}/progress${queryString({ content_version, mode })}`),

  saveListeningProgress: (
    id: number,
    progress: Omit<ListeningProgress, "status" | "updated_at">,
    signal?: AbortSignal,
  ) => request<ListeningProgress>(`/listening/tests/${id}/progress`, {
    method: "PUT",
    body: JSON.stringify(progress),
    signal,
  }),

  submitListening: (
    id: number,
    payload: {
      content_version: string;
      mode: ListeningMode;
      submission_key: string;
      answers: { question_id: number; answer: AnswerValue; marked_for_review?: boolean }[];
      duration_seconds?: number;
    }
  ) => request<ListeningSubmitResult>(`/listening/tests/${id}/submit`, {
    method: "POST",
    body: JSON.stringify(payload),
  }),

  getListeningReview: (attemptId: number) =>
    request<ListeningReview>(`/listening/attempts/${attemptId}`),
};
