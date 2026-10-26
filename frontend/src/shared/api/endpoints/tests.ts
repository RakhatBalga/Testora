import { request } from "../http";
import type { AnswerValue, AttemptResult, AttemptSummary, Test, TestDetail } from "../types";

export const testsApi = {
  listTests: () => request<Test[]>("/tests"),

  getTest: (id: number) => request<TestDetail>(`/tests/${id}`),

  submit: (
    test_id: number,
    answers: { question_id: number; answer: AnswerValue; marked_for_review?: boolean }[],
    duration_seconds?: number
  ) =>
    request<AttemptResult>("/results/submit", {
      method: "POST",
      body: JSON.stringify({ test_id, answers, duration_seconds }),
    }),

  listAttempts: () => request<AttemptSummary[]>("/results"),

  getAttempt: (id: number) => request<AttemptResult>(`/results/${id}`),
};
