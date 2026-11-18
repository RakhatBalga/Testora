import { afterEach, expect, it } from "vitest";
import { clearWritingSubmissionKey, writingSubmissionKey } from "./submissionKey";

afterEach(() => localStorage.clear());

it("reuses the key for the same text, across reloads", () => {
  const key = writingSubmissionKey("draft", "An essay.");
  expect(key).toMatch(/^[A-Za-z0-9._:-]{8,80}$/);
  expect(writingSubmissionKey("draft", "An essay.")).toBe(key);
});

it("issues a new key when the text changed, and binds it to the new text", () => {
  const first = writingSubmissionKey("draft", "An essay.");
  const second = writingSubmissionKey("draft", "An essay, edited.");
  expect(second).not.toBe(first);
  expect(writingSubmissionKey("draft", "An essay, edited.")).toBe(second);
  // Going back to the old text is a new attempt too, not the first key.
  expect(writingSubmissionKey("draft", "An essay.")).not.toBe(first);
});

it("starts over after clearing or a corrupt entry, and keeps drafts apart", () => {
  const first = writingSubmissionKey("draft", "An essay.");
  expect(writingSubmissionKey("other", "An essay.")).not.toBe(first);
  clearWritingSubmissionKey("draft");
  const second = writingSubmissionKey("draft", "An essay.");
  expect(second).not.toBe(first);
  localStorage.setItem("draft-submission-key", "not json");
  expect(writingSubmissionKey("draft", "An essay.")).not.toBe(second);
});
