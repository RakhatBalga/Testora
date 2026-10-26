import { request, queryString } from "../http";
import type { DiagnosticState, LearningDashboard, NotebookPage, StudyPlan, StudyPlanItem } from "../types";

export const learningApi = {
  getLearningDashboard: () => request<LearningDashboard>("/learning/dashboard"),

  getDiagnostic: () => request<DiagnosticState>("/learning/diagnostic"),

  startDiagnostic: (skills: ("writing" | "reading")[]) =>
    request<DiagnosticState>("/learning/diagnostic/start", {
      method: "POST",
      body: JSON.stringify({ skills }),
    }),

  refreshDiagnostic: () => request<DiagnosticState>("/learning/diagnostic/refresh", { method: "POST" }),

  acceptDiagnosticLevel: () => request<DiagnosticState>("/learning/diagnostic/accept-level", { method: "POST" }),

  skipDiagnostic: () => request<DiagnosticState>("/learning/diagnostic/skip", { method: "POST" }),

  getStudyPlan: () => request<StudyPlan>("/learning/study-plan"),

  recalculateStudyPlan: () => request<StudyPlan>("/learning/study-plan/recalculate", { method: "POST" }),

  resetStudyPlan: () => request<StudyPlan>("/learning/study-plan/reset", { method: "POST" }),

  updateStudyPlanItem: (id: number, status: "completed" | "skipped") =>
    request<StudyPlanItem>(`/learning/study-plan/${id}`, {
      method: "PATCH",
      body: JSON.stringify({ status }),
    }),

  getMistakes: (filters: { skill?: string; status?: string; page?: number; page_size?: number } = {}) =>
    request<NotebookPage>(`/learning/mistakes${queryString(filters)}`),

  updateMistakeStatus: (skill: "writing" | "reading" | "listening", sourceId: number, status: "new" | "reviewing" | "mastered") =>
    request<{ skill: string; source_id: number; status: string }>(`/learning/mistakes/${skill}/${sourceId}`, {
      method: "PATCH",
      body: JSON.stringify({ status }),
    }),

  // ---- Vocabulary builder ----
};
