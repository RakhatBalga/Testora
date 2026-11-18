import { afterEach, expect, it } from "vitest";
import { clearExamSubmissionKey, consumeRetakeFlag, examStorageKey, examSubmissionKey } from "./storage";

afterEach(() => {
  localStorage.clear();
  window.history.replaceState(null, "", "/");
});

it("scopes keys per user and per test", () => {
  expect(examStorageKey("reading", "ann", 4)).toBe("reading-ann-4");
  expect(examStorageKey("reading", "bob", 4)).not.toBe(examStorageKey("reading", "ann", 4));
  expect(examStorageKey("reading", null, 4)).toBe("reading-anonymous-4");
});

it("reuses one submission key per attempt, across reloads", () => {
  const first = examSubmissionKey("reading-ann-4");
  // Accepted by the backend schema: 8-80 chars of [A-Za-z0-9._:-].
  expect(first).toMatch(/^[A-Za-z0-9._:-]{8,80}$/);
  expect(examSubmissionKey("reading-ann-4")).toBe(first);
  expect(localStorage.getItem("reading-ann-4-submission-key")).toBe(first);
  expect(examSubmissionKey("reading-ann-5")).not.toBe(first);
});

it("issues a new submission key after the attempt is cleared", () => {
  const first = examSubmissionKey("reading-ann-4");
  clearExamSubmissionKey("reading-ann-4");
  expect(examSubmissionKey("reading-ann-4")).not.toBe(first);
});

it("consumes ?retake=1 once and keeps the rest of the URL", () => {
  window.history.replaceState(null, "", "/reading/4?retake=1&from=result#top");
  expect(consumeRetakeFlag()).toBe(true);
  expect(window.location.pathname + window.location.search + window.location.hash).toBe("/reading/4?from=result#top");
  // A reload now sees no flag, so the stored result is not deleted again.
  expect(consumeRetakeFlag()).toBe(false);
});

it("ignores a URL without the retake flag", () => {
  window.history.replaceState(null, "", "/reading/4?attempt=9");
  expect(consumeRetakeFlag()).toBe(false);
  expect(window.location.search).toBe("?attempt=9");
});
