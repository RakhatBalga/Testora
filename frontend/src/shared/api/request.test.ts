import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { api } from "./api";
import { NetworkError, isNetworkError } from "./errors";
import { REQUEST_TIMEOUT_MS } from "./http";

beforeEach(() => vi.useFakeTimers());
afterEach(() => {
  vi.useRealTimers();
  vi.unstubAllGlobals();
  sessionStorage.clear();
});

const json = (body: unknown, status = 200) => new Response(JSON.stringify(body), { status });

it("times out a stalled request with a friendly NetworkError", async () => {
  vi.stubGlobal("fetch", vi.fn((_u, o: RequestInit) => new Promise((_, reject) => {
    o.signal!.addEventListener("abort", () => reject(new DOMException("Aborted", "AbortError")));
  })));
  // POST: not retried, so the timeout surfaces after one attempt.
  const result = expect(api.submitDailyQuiz([1])).rejects.toSatisfy(
    (e) => isNetworkError(e) && e.kind === "timeout",
  );
  await vi.advanceTimersByTimeAsync(REQUEST_TIMEOUT_MS);
  await result;
  expect(fetch).toHaveBeenCalledTimes(1);
});

it("retries an idempotent GET after a network error", async () => {
  const fetchMock = vi.fn()
    .mockRejectedValueOnce(new TypeError("Failed to fetch"))
    .mockResolvedValueOnce(json([{ id: 1 }]));
  vi.stubGlobal("fetch", fetchMock);
  const result = api.listTests();
  await vi.advanceTimersByTimeAsync(1_000);
  await expect(result).resolves.toEqual([{ id: 1 }]);
  expect(fetchMock).toHaveBeenCalledTimes(2);
});

it("retries gateway errors and gives up with a waking-up message", async () => {
  const fetchMock = vi.fn().mockImplementation(() => Promise.resolve(new Response("bad gateway", { status: 502 })));
  vi.stubGlobal("fetch", fetchMock);
  const result = expect(api.listTests()).rejects.toBeInstanceOf(NetworkError);
  await vi.advanceTimersByTimeAsync(3_000);
  await result;
  expect(fetchMock).toHaveBeenCalledTimes(3);
});

it("does not retry non-idempotent requests", async () => {
  const fetchMock = vi.fn().mockRejectedValue(new TypeError("Failed to fetch"));
  vi.stubGlobal("fetch", fetchMock);
  await expect(api.submitDailyQuiz([1])).rejects.toBeInstanceOf(NetworkError);
  expect(fetchMock).toHaveBeenCalledTimes(1);
});

it("does not retry application errors", async () => {
  const fetchMock = vi.fn().mockResolvedValue(json({ detail: "Not found" }, 404));
  vi.stubGlobal("fetch", fetchMock);
  await expect(api.getTest(1)).rejects.toThrow("Not found");
  expect(fetchMock).toHaveBeenCalledTimes(1);
});

it("lets the caller cancel without it being reported as a timeout", async () => {
  vi.stubGlobal("fetch", vi.fn((_u, o: RequestInit) => new Promise((_, reject) => {
    o.signal!.addEventListener("abort", () => reject(new DOMException("Aborted", "AbortError")));
  })));
  const controller = new AbortController();
  const result = expect(
    api.saveListeningProgress(1, {} as never, controller.signal),
  ).rejects.toMatchObject({ name: "AbortError" });
  controller.abort();
  await result;
});
