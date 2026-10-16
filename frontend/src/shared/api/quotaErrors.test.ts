import { afterEach, expect, it, vi } from "vitest";
import { api } from "./api";

afterEach(() => vi.unstubAllGlobals());

it.each([
  () => api.submitWriting(1, "essay"),
  () => api.submitSpeaking(1, new Blob(["audio"])),
  () => api.enrichWord(1),
])("shows the daily reset time for AI operations", async (submit) => {
  const reset = "2026-10-17T00:00:00+00:00";
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify({ detail: {
    code: "ai_daily_limit", message: "Daily AI limit reached.", resets_at: reset,
  } }), { status: 429 })));
  await expect(submit()).rejects.toThrow(`Available again at ${new Date(reset).toLocaleString()}`);
});

it("explains that free reviews do not reset daily", async () => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify({ detail: {
    code: "ai_free_reviews_exhausted", message: "You've used your 2 free writing reviews. This allowance does not reset daily.",
  } }), { status: 403 })));
  await expect(api.submitWriting(1, "essay")).rejects.toThrow("does not reset daily");
});

it("preserves ordinary validation messages", async () => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify({ detail: [
    { loc: ["body", "text"], msg: "Too short" },
  ] }), { status: 422 })));
  await expect(api.submitWriting(1, "essay")).rejects.toThrow("text: Too short");
});
