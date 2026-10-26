import { act, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { useDeadlineCountdown } from "./useDeadlineCountdown";

beforeEach(() => vi.useFakeTimers());
afterEach(() => vi.useRealTimers());

it("shows the full time on start, never a 00:00 flash, then finishes once", async () => {
  const onDone = vi.fn();
  const values: number[] = [];
  const { result, rerender } = renderHook(({ run }) => {
    const v = useDeadlineCountdown(run, 5, onDone);
    values.push(v);
    return v;
  }, { initialProps: { run: false } });
  rerender({ run: true });
  expect(values.slice(values.lastIndexOf(5) - 0)).not.toContain(0);
  expect(result.current).toBe(5);
  await act(async () => { await vi.advanceTimersByTimeAsync(5_250); });
  expect(onDone).toHaveBeenCalledTimes(1);
  expect(result.current).toBe(0);
});

it("restarts from the full time on the next run", async () => {
  const { result, rerender } = renderHook(({ run }) => useDeadlineCountdown(run, 3, vi.fn()), { initialProps: { run: true } });
  await act(async () => { await vi.advanceTimersByTimeAsync(3_500); });
  expect(result.current).toBe(0);
  rerender({ run: false });
  rerender({ run: true });
  expect(result.current).toBe(3);
});
