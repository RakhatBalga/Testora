import { afterEach, expect, it, vi } from "vitest";
import { storeAuth } from "@/shared/api";
import { createProgressWriter, listeningSessionKey, restoreProgress, type ProgressInput } from "./progress";

const progress: ProgressInput = { content_version: "1.0.1", mode: "practice", answers: { "1": "Hartley" }, current_section: 1, audio_position: 150, max_audio_position: 160 };
afterEach(() => { localStorage.clear(); sessionStorage.clear(); vi.restoreAllMocks(); });

it("recovers answers, section and audio immediately, before the debounce can save", () => {
  const save = vi.fn();
  createProgressWriter("session", save, vi.fn()).record(progress);
  expect(save).not.toHaveBeenCalled();
  expect(restoreProgress("session", null)).toMatchObject(progress);
});

it("isolates drafts by account, test, version and mode", () => {
  storeAuth("token", "first");
  const key = listeningSessionKey(1, "1.0.1");
  createProgressWriter(key, vi.fn(), vi.fn()).record(progress);
  storeAuth("other-token", "second");
  expect(restoreProgress(listeningSessionKey(1, "1.0.1"), null)).toBeNull();
  storeAuth("token", "first");
  expect(restoreProgress(listeningSessionKey(2, "1.0.1"), null)).toBeNull();
  expect(restoreProgress(listeningSessionKey(1, "1.0.2"), null)).toBeNull();
  expect(restoreProgress(listeningSessionKey(1, "1.0.1", "exam"), null)).toBeNull();
});

it("serializes writes and retains newer local changes while the old save is in flight", async () => {
  let resolve!: () => void;
  const save = vi.fn().mockImplementationOnce(() => new Promise<void>((done) => { resolve = done; })).mockResolvedValue(undefined);
  const writer = createProgressWriter("session", save, vi.fn());
  writer.record(progress);
  const first = writer.flush();
  const latest = { ...progress, answers: { "1": "new answer" } };
  writer.record(latest);
  void writer.flush();
  expect(save).toHaveBeenCalledTimes(1);
  expect(restoreProgress("session", null)?.answers).toEqual(latest.answers);
  resolve();
  await first;
  expect(save).toHaveBeenCalledTimes(2);
  expect(save).toHaveBeenLastCalledWith(latest);
  expect(restoreProgress("session", null)).toBeNull();
});

it("retains failed saves for retry and reports the failure", async () => {
  const save = vi.fn().mockRejectedValueOnce(new Error("offline")).mockResolvedValue(undefined);
  const report = vi.fn();
  const writer = createProgressWriter("session", save, report);
  writer.record(progress);
  await writer.flush();
  expect(restoreProgress("session", null)).toMatchObject(progress);
  expect(report).toHaveBeenLastCalledWith(expect.stringContaining("not synced"));
  await writer.flush();
  expect(save).toHaveBeenCalledTimes(2);
  expect(report).toHaveBeenLastCalledWith("");
});

it("waits for an in-flight save before submission and blocks further saves", async () => {
  let resolve!: () => void;
  const save = vi.fn(() => new Promise<void>((done) => { resolve = done; }));
  const writer = createProgressWriter("session", save, vi.fn());
  writer.record(progress);
  void writer.flush();
  writer.record({ ...progress, current_section: 2 });
  const submit = vi.fn();
  const stopping = writer.stop().then(submit);
  await Promise.resolve();
  expect(submit).not.toHaveBeenCalled();
  resolve();
  await stopping;
  await writer.flush();
  expect(save).toHaveBeenCalledTimes(1);
  expect(submit).toHaveBeenCalledTimes(1);
  writer.clear();
  expect(restoreProgress("session", null)).toBeNull();
});

it("does not resurrect a draft older than a submitted server attempt", () => {
  localStorage.setItem("session-draft", JSON.stringify({ progress, updatedAt: Date.parse("2026-10-18T10:00:00Z") }));
  expect(restoreProgress("session", { ...progress, status: "submitted", updated_at: "2026-10-18T10:01:00" })).toBeNull();
});

it("keeps unsynced edits even if an older request received a later server timestamp", () => {
  localStorage.setItem("session-draft", JSON.stringify({ progress, updatedAt: Date.parse("2026-10-18T10:00:00Z") }));
  const saved = { ...progress, answers: { "1": "old answer" }, status: "in_progress", updated_at: "2026-10-18T10:01:00Z" };
  expect(restoreProgress("session", saved)?.answers).toEqual(progress.answers);
});

it("ignores corrupt browser drafts", () => {
  localStorage.setItem("session-draft", "broken json");
  expect(restoreProgress("session", null)).toBeNull();
});
