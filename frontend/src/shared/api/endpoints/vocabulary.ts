import { request, queryString } from "../http";
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
    request<SavedWord>(`/vocabulary/words/${wordId}/enrich`, { method: "POST" }),

  setWordTraining: (wordId: number, training: boolean) =>
    request<SavedWord>(`/vocabulary/words/${wordId}/training`, {
      method: "PATCH",
      body: JSON.stringify({ training }),
    }),

  getDailyQuiz: () => request<DailyQuiz>("/vocabulary/daily-quiz"),

  submitDailyQuiz: (answers: (number | null)[]) =>
    request<QuizResult>("/vocabulary/daily-quiz/submit", {
      method: "POST",
      body: JSON.stringify({ answers }),
    }),
};
