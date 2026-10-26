import { describe, expect, it } from "vitest";
import type { AttemptSummary } from "@/shared/api";
import { buildActivity, buildRecentItems, summarizeBands } from "./stats";

const attempt = (id: number, band: number | null, type = "reading", created_at = "2026-03-10T10:00:00Z") =>
  ({ id, test_id: id, test_title: `T${id}`, test_type: type, score: 20, total: 40, band, created_at } as unknown as AttemptSummary);

describe("summarizeBands", () => {
  it("averages to half bands and per skill", () => {
    const attempts = [attempt(1, 6), attempt(2, 7, "listening")];
    const r = summarizeBands({ attempts, writing: [], speaking: [] });
    expect(r.avgBand).toBe(6.5);
    expect(r.bestBand).toBe(7);
    expect(r.skillBands.reading).toBe(6);
    expect(r.skillBands.listening).toBe(7);
    expect(r.skillBands.writing).toBeNull();
  });

  it("returns nulls when nothing is graded", () => {
    expect(summarizeBands({ attempts: [attempt(1, null)], writing: [], speaking: [] }).avgBand).toBeNull();
  });
});

describe("buildRecentItems", () => {
  it("sorts newest first and routes listening results", () => {
    const attempts = [
      attempt(1, 6, "reading", "2026-03-01T00:00:00Z"),
      attempt(2, 6, "listening", "2026-03-05T00:00:00Z"),
    ];
    const items = buildRecentItems({ attempts, writing: [], speaking: [] });
    expect(items.map((i) => i.id)).toEqual(["attempt-2", "attempt-1"]);
    expect(items[0].href).toBe("/listening/result/2");
  });
});

describe("buildActivity", () => {
  it("counts today's sessions and the current streak", () => {
    const now = new Date(2026, 2, 10, 12);
    const attempts = [attempt(1, 6, "reading", new Date(2026, 2, 10, 9).toISOString()), attempt(2, 6, "reading", new Date(2026, 2, 9, 9).toISOString())];
    const a = buildActivity({ attempts, writing: [], speaking: [] }, now);
    expect(a.total).toBe(2);
    expect(a.currentStreak).toBe(2);
    expect(a.weeks.every((w) => w.length === 7)).toBe(true);
  });
});
