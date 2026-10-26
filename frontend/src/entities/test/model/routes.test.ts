import { describe, expect, it } from "vitest";
import { examHref } from "./routes";

describe("examHref (retake routing)", () => {
  it("routes by test type", () => {
    expect(examHref("reading", 7)).toBe("/reading/7");
    expect(examHref("listening", 3)).toBe("/listening/3");
  });
  it("marks a retake so the stored result is cleared", () => {
    expect(examHref("reading", 7, { retake: true })).toBe("/reading/7?retake=1");
  });
  it("never points at the removed legacy /test route", () => {
    expect(examHref("mystery", 1)).not.toContain("/test/");
  });
});
