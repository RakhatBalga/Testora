import { request, queryString } from "../http";
import type { BandGapResult, BandTrajectoryResult, Blocker, DailyPlan, Recommendation, RecurringMistake, Streak, Weakness } from "../types";

export const analyticsApi = {
  getWeaknesses: (limit = 6) =>
    request<{ weaknesses: Weakness[] }>(`/analytics/weaknesses?limit=${limit}`),

  getBlockers: (target?: number) =>
    request<{ blockers: Blocker[] }>(`/analytics/blockers${queryString({ target })}`),

  getBandGap: (target?: number) =>
    request<BandGapResult>(`/analytics/band-gap${queryString({ target })}`),

  getBandTrajectory: () => request<BandTrajectoryResult>("/analytics/band-trajectory"),

  getDailyPlan: (target?: number, limit = 3) =>
    request<DailyPlan>(`/analytics/daily-plan${queryString({ target, limit })}`),

  getStreak: () => request<Streak>("/analytics/streak"),

  getRecurringMistakes: (limit = 6) =>
    request<{ recurring: RecurringMistake[] }>(`/analytics/recurring-mistakes?limit=${limit}`),

  getRecommendations: (target?: number, limit = 5) =>
    request<{ recommendations: Recommendation[] }>(
      `/analytics/recommendations${queryString({ target, limit })}`
    ),
};
