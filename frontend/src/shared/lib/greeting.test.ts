import { describe, expect, it } from "vitest";
import { greeting } from "./greeting";

// greeting() buckets the local hour into three time-of-day phrases. Build the
// dates from explicit hours so the test does not depend on when it runs.
function at(hour: number): Date {
  const d = new Date();
  d.setHours(hour, 0, 0, 0);
  return d;
}

describe("greeting", () => {
  it("says good morning before noon", () => {
    expect(greeting(at(0))).toBe("Good morning");
    expect(greeting(at(11))).toBe("Good morning");
  });

  it("says good afternoon from noon until 18:00", () => {
    expect(greeting(at(12))).toBe("Good afternoon");
    expect(greeting(at(17))).toBe("Good afternoon");
  });

  it("says good evening at 18:00 and later", () => {
    expect(greeting(at(18))).toBe("Good evening");
    expect(greeting(at(23))).toBe("Good evening");
  });
});
