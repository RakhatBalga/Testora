import { expect, it } from "vitest";
import { examStorageKey } from "./storage";

it("scopes keys per user and per test", () => {
  expect(examStorageKey("reading", "ann", 4)).toBe("reading-ann-4");
  expect(examStorageKey("reading", "bob", 4)).not.toBe(examStorageKey("reading", "ann", 4));
  expect(examStorageKey("reading", null, 4)).toBe("reading-anonymous-4");
});
