import { describe, expect, it } from "vitest";
import { formatClockSeconds, remainingSeconds, resolveTimerStart } from "./examTimer";

describe("remainingSeconds", () => {
  it("derives time from the deadline, rounding up, never negative", () => {
    expect(remainingSeconds(10_000, 0)).toBe(10);
    expect(remainingSeconds(10_001, 0)).toBe(11);
    expect(remainingSeconds(1_000, 5_000)).toBe(0);
  });

  it("reflects real elapsed time after a long background pause", () => {
    const deadline = 60 * 60 * 1000;
    // 20 minutes spent in another app: ~40 minutes left, not 59.
    expect(remainingSeconds(deadline, 20 * 60 * 1000)).toBe(40 * 60);
  });
});

describe("resolveTimerStart", () => {
  const now = 1_000_000;
  it("starts fresh without saved state", () => {
    expect(resolveTimerStart(null, now, 1200)).toEqual({ kind: "fresh" });
  });
  it("resumes a running deadline", () => {
    expect(resolveTimerStart({ deadline: now + 5_000, pausedRemaining: null }, now, 1200))
      .toEqual({ kind: "running", deadline: now + 5_000 });
  });
  it("clamps a stale longer deadline to the real duration", () => {
    expect(resolveTimerStart({ deadline: now + 3_600_000, pausedRemaining: null }, now, 1200))
      .toEqual({ kind: "running", deadline: now + 1_200_000 });
  });
  it("restores a paused timer, clamped", () => {
    expect(resolveTimerStart({ deadline: null, pausedRemaining: 3000 }, now, 1200))
      .toEqual({ kind: "paused", remaining: 1200 });
  });
  it("reports an expired deadline instead of granting extra time", () => {
    expect(resolveTimerStart({ deadline: now - 1, pausedRemaining: null }, now, 1200))
      .toEqual({ kind: "expired" });
  });
});

describe("formatClockSeconds", () => {
  it("formats mm:ss and a placeholder", () => {
    expect(formatClockSeconds(3605)).toBe("60:05");
    expect(formatClockSeconds(null)).toBe("--:--");
  });
});
