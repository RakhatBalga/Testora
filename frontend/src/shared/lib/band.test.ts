import { expect, it } from "vitest";
import { bandBadgeClass, bandTextClass } from "./band";
import { formatDuration } from "./format";

it("picks tone by band thresholds", () => {
  expect(bandBadgeClass(null)).toContain("slate");
  expect(bandBadgeClass(7)).toContain("emerald");
  expect(bandBadgeClass(6)).toContain("amber");
  expect(bandTextClass(4.5)).toBe("text-red-600");
});

it("formats durations", () => {
  expect(formatDuration(65)).toBe("1m 5s");
  expect(formatDuration(42)).toBe("42s");
  expect(formatDuration(null)).toBeNull();
});
