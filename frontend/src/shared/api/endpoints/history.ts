import { request } from "../http";
import type { BreakdownItem, CompareResult, Feedback, HistoryItem } from "../types";

export const historyApi = {
  getHistory: (skill?: string, sort = "newest", page = 1, pageSize = 10) => {
    const params = new URLSearchParams({ sort, page: String(page), page_size: String(pageSize) });
    if (skill) params.set("skill", skill);
    return request<{ items: HistoryItem[]; total: number; page?: number; page_size?: number }>(`/history?${params}`);
  },

  getHistoryItem: (itemId: string) => request<HistoryItem & { feedback?: Feedback | null; breakdown?: BreakdownItem[] }>(`/history/${itemId}`),

  compareHistory: (a: string, b: string) =>
    request<CompareResult>(`/history/compare?a=${encodeURIComponent(a)}&b=${encodeURIComponent(b)}`),
};
