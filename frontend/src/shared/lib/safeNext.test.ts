import { describe, expect, it } from "vitest";
import { safeNext } from "./safeNext";

describe("safeNext", () => {
  it.each(["/", "/writing/12", "/history?page=2", "/result/3#top"])("keeps %s", (p) => {
    expect(safeNext(p)).toBe(p);
  });

  it.each([
    "//evil.example/x",
    "/\\evil.example",
    "https://evil.example",
    "javascript:alert(1)",
    "evil.example",
    "/\t/evil.example",
    "/a\\b",
    "",
  ])("rejects %j", (p) => {
    expect(safeNext(p)).toBe("/");
  });

  it("handles null and custom fallback", () => {
    expect(safeNext(null)).toBe("/");
    expect(safeNext(undefined, "/home")).toBe("/home");
  });
});
