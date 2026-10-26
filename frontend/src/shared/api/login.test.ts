import { afterEach, expect, it, vi } from "vitest";
import { api, getStoredAuthToken, storeAuth } from "./api";

afterEach(() => {
  vi.useRealTimers();
  vi.unstubAllGlobals();
  sessionStorage.clear();
  localStorage.clear();
});

it("reports invalid credentials without clearing an existing session", async () => {
  storeAuth("existing-token", "existing-user");
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(null, { status: 401 })));
  await expect(api.login("user", "wrong")).rejects.toThrow("Incorrect email, username or password.");
  expect(getStoredAuthToken()).toBe("existing-token");
  expect(fetch).toHaveBeenCalledWith(expect.stringContaining("/auth/login"), expect.objectContaining({
    headers: { "Content-Type": "application/json" },
  }));
});

it.each(["headers", "body"])("aborts a login stalled on response %s after 90 seconds", async (stage) => {
  vi.useFakeTimers();
  let signal!: AbortSignal;
  vi.stubGlobal("fetch", vi.fn((_url, options: RequestInit) => {
    signal = options.signal!;
    const pending = new Promise((_, reject) => {
      signal.addEventListener("abort", () => reject(new DOMException("Aborted", "AbortError")));
    });
    return stage === "headers" ? pending : Promise.resolve({ ok: true, json: () => pending });
  }));
  const result = expect(api.login("user", "password")).rejects.toThrow("Sign-in is taking too long.");
  await vi.advanceTimersByTimeAsync(89_999);
  expect(signal.aborted).toBe(false);
  await vi.advanceTimersByTimeAsync(1);
  await result;
  expect(signal.aborted).toBe(true);
  expect(vi.getTimerCount()).toBe(0);
});

it("returns the token and cleans up the timer on success", async () => {
  vi.useFakeTimers();
  const token = { access_token: "new-token", token_type: "bearer" };
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify(token))));
  await expect(api.login("user", "password")).resolves.toEqual(token);
  expect(vi.getTimerCount()).toBe(0);
});

it("explains connection errors and cleans up the timer", async () => {
  vi.useFakeTimers();
  vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("Failed to fetch")));
  await expect(api.login("user", "password")).rejects.toThrow("Check your connection");
  expect(vi.getTimerCount()).toBe(0);
});

it("preserves server rate-limit messages", async () => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(
    JSON.stringify({ detail: "Too many attempts. Please wait." }), { status: 429 },
  )));
  await expect(api.login("user", "password")).rejects.toThrow("Too many attempts. Please wait.");
});

it("still expires invalid sessions on protected requests", async () => {
  window.history.replaceState({}, "", "/login");
  storeAuth("expired-token", "user");
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(null, { status: 401 })));
  await expect(api.listAttempts()).rejects.toThrow("Your session has expired.");
  expect(getStoredAuthToken()).toBeNull();
});
