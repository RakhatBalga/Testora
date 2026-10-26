/** Where to take (or retake) a test, by its type. Every type has its own exam screen. */
export function examHref(testType: string, testId: number): string {
  if (testType === "listening") return `/listening/${testId}`;
  if (testType === "reading") return `/reading/${testId}`;
  // Unknown/legacy type: send the user to the library rather than a dead route.
  return "/tests/reading";
}
