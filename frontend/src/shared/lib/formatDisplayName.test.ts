import { describe, expect, it } from "vitest";
import { formatDisplayName } from "./formatDisplayName";

describe("formatDisplayName", () => {
  it("title-cases a plain username", () => {
    expect(formatDisplayName("olzhas")).toBe("Olzhas");
  });

  it("strips the domain from an email-style username", () => {
    expect(formatDisplayName("olzhas@gmail.com")).toBe("Olzhas");
  });

  it("splits separators into spaced, title-cased words", () => {
    expect(formatDisplayName("olzhas.k_bek-uly")).toBe("Olzhas K Bek Uly");
  });

  it("falls back to 'there' for null, empty, or whitespace input", () => {
    expect(formatDisplayName(null)).toBe("there");
    expect(formatDisplayName("")).toBe("there");
    expect(formatDisplayName("   ")).toBe("there");
  });
});
