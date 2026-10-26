import { act, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { useExamTimer } from "./useExamTimer";

beforeEach(() => {
  vi.useFakeTimers();
  localStorage.clear();
});
afterEach(() => vi.useRealTimers());

const advance = (ms: number) => act(async () => { await vi.advanceTimersByTimeAsync(ms); });

it("waits for the real duration before starting", async () => {
  const { result, rerender } = renderHook(({ d }) => useExamTimer("t", d, vi.fn()), { initialProps: { d: null as number | null } });
  await advance(5_000);
  expect(result.current.remaining).toBeNull();
  expect(localStorage.getItem("t-timer")).toBeNull();
  rerender({ d: 1200 });
  await advance(10);
  expect(result.current.remaining).toBe(1200);
});

it("uses the stored deadline: wall-clock jumps are not lost", async () => {
  const onExpire = vi.fn();
  const { result } = renderHook(() => useExamTimer("t", 600, onExpire));
  await advance(10);
  expect(result.current.remaining).toBe(600);
  // Simulate a suspended tab: the clock jumps 5 minutes, no interval ticks ran.
  vi.setSystemTime(Date.now() + 300_000);
  act(() => { document.dispatchEvent(new Event("visibilitychange")); });
  expect(result.current.remaining).toBe(300);
  expect(onExpire).not.toHaveBeenCalled();
});

it("fires onExpire once when time runs out", async () => {
  const onExpire = vi.fn();
  renderHook(() => useExamTimer("t", 3, onExpire));
  await advance(10);
  await advance(4_000);
  expect(onExpire).toHaveBeenCalledTimes(1);
  await advance(5_000);
  expect(onExpire).toHaveBeenCalledTimes(1);
});

it("restarts instead of submitting when a stale deadline has no saved work", async () => {
  localStorage.setItem("t-timer", JSON.stringify({ deadline: Date.now() - 1000, pausedRemaining: null }));
  const onExpire = vi.fn();
  const { result } = renderHook(() => useExamTimer("t", 600, onExpire, { shouldSubmitStale: () => false }));
  await advance(10);
  expect(result.current.remaining).toBe(600);
  expect(onExpire).not.toHaveBeenCalled();
});

it("expires immediately when a stale deadline has saved answers", async () => {
  localStorage.setItem("t-timer", JSON.stringify({ deadline: Date.now() - 1000, pausedRemaining: null }));
  const onExpire = vi.fn();
  const { result } = renderHook(() => useExamTimer("t", 600, onExpire, { shouldSubmitStale: () => true }));
  await advance(10);
  expect(result.current.remaining).toBe(0);
  expect(onExpire).toHaveBeenCalledTimes(1);
});

it("clamps a 60-minute stored deadline to a 20-minute test", async () => {
  localStorage.setItem("t-timer", JSON.stringify({ deadline: Date.now() + 3_600_000, pausedRemaining: null }));
  const { result } = renderHook(() => useExamTimer("t", 1200, vi.fn()));
  await advance(10);
  expect(result.current.remaining).toBe(1200);
});

it("pauses and resumes without losing time", async () => {
  const { result } = renderHook(() => useExamTimer("t", 600, vi.fn()));
  await advance(10);
  await advance(60_000);
  act(() => result.current.pause());
  const left = result.current.remaining;
  await advance(120_000);
  expect(result.current.remaining).toBe(left);
  act(() => result.current.resume());
  await advance(1_000);
  expect(result.current.remaining).toBe((left as number) - 1);
});
