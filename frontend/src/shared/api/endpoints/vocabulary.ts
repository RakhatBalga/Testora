import { AI_TIMEOUT_MS, queryString, request, retryWhenInProgress } from "../http";
import type { DailyQuiz, QuizResult, SavedWord, VocabularyList } from "../types";

export const vocabularyApi = {
  saveWord: (payload: { word: string; context?: string | null; source?: string; source_ref?: string }) =>
    request<SavedWord>("/vocabulary/words", { method: "POST", body: JSON.stringify(payload) }),

  listWords: (filters: { training?: boolean; page?: number; page_size?: number } = {}) => {
    const params: Record<string, string | number | undefined> = {
      page: filters.page,
      page_size: filters.page_size,
    };
    if (filters.training) params.training = "true";
    return request<VocabularyList>(`/vocabulary/words${queryString(params)}`);
  },

  deleteWord: (wordId: number) =>
    request<{ deleted: number }>(`/vocabulary/words/${wordId}`, { method: "DELETE" }),

  enrichWord: (wordId: number) =>
    retryWhenInProgress(() =>
      request<SavedWord>(`/vocabulary/words/${wordId}/enrich`, { method: "POST" }, { timeoutMs: AI_TIMEOUT_MS, retries: 0 }),
    ),

  setWordTraining: (wordId: number, training: boolean) =>
    request<SavedWord>(`/vocabulary/words/${wordId}/training`, {
      method: "PATCH",
      body: JSON.stringify({ training }),
    }),

  // Calls the AI synchronously: long timeout, and no GET retry (a retry would hit 409 in progress).
  getDailyQuiz: () =>
    retryWhenInProgress(() => request<DailyQuiz>("/vocabulary/daily-quiz", {}, { timeoutMs: AI_TIMEOUT_MS, retries: 0 })),

  submitDailyQuiz: (answers: (number | null)[]) =>
    request<QuizResult>("/vocabulary/daily-quiz/submit", {
      method: "POST",
      body: JSON.stringify({ answers }),
    }),
};
