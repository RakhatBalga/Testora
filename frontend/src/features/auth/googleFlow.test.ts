import { afterEach, describe, expect, it, vi } from "vitest";
import { beginGoogleFlow, consumeGoogleFlow } from "./googleFlow";

afterEach(() => { sessionStorage.clear(); vi.useRealTimers(); });

describe("Google callback binding", () => {
  it("accepts the matching state once", () => {
    const state = beginGoogleFlow();
    expect(state).toMatch(/^[A-Za-z0-9_-]{43}$/);
    expect(consumeGoogleFlow(state)).toBe(state);
    expect(() => consumeGoogleFlow(state)).toThrow();
  });
  it.each([null, "attacker-state"])("rejects missing or foreign state: %s", (state) => {
    beginGoogleFlow();
    expect(() => consumeGoogleFlow(state)).toThrow();
  });
  it("rejects unsolicited callbacks even with a state", () => {
    expect(() => consumeGoogleFlow("attacker-state")).toThrow();
  });
  it("rejects expired flows", () => {
    vi.useFakeTimers();
    const state = beginGoogleFlow();
    vi.advanceTimersByTime(10 * 60 * 1000);
    expect(() => consumeGoogleFlow(state)).toThrow();
  });
  it("uses different unpredictable state for each attempt", () => {
    const old = beginGoogleFlow();
    expect(beginGoogleFlow()).not.toBe(old);
    expect(() => consumeGoogleFlow(old)).toThrow();
  });
});
